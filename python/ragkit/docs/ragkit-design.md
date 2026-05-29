# ragkit — Design Document

**Location:** `dev-utils/python/ragkit/`
**Version:** 0.1.0
**Status:** Pre-implementation design — approved before coding begins
**Part of:** Project Crew / dev-utils ecosystem

---

## Purpose

ragkit builds and queries a local RAG (Retrieval-Augmented Generation)
index from a folder of structured documents. Given a query, it returns
the most relevant text chunks for injection into an LLM prompt.

Primary consumer: designing-gemma, where experiment prompts can be
augmented with retrieved context from a curated document collection —
design docs, coding rules, website themes, existing examples.

General enough to be useful anywhere a local document collection needs
to inform LLM generation without dumping the entire collection into the
prompt.

---

## Tagline

*"for when the model needs to know what you've already decided"*

---

## The Problem It Solves

designing-gemma currently injects repo context (skeletons, file content)
as a single assembled block with a character budget. This is "full dump"
— useful for code structure, but not for document knowledge.

ragkit enables a different class of experiment:

- "Write a script that follows the project rules" → retrieves
  `coding_rules.md`, `config_rules.md`, `project_rules.md`
- "Create a new page using the existing theme" → retrieves
  `website_rules.md`, theme CSS, existing page samples
- "Write a README for this package" → retrieves existing READMEs
  as style exemplars

The model sees only the relevant chunks, not the entire document
collection. This is semantically targeted injection.

---

## Design Constraints

**Documents fed to ragkit must be well-structured.** This is a hard
requirement, not a preference. Poorly structured documents produce
poor chunks and poor retrieval. ragkit is opinionated: garbage in,
garbage out.

**Acceptable document types:**
- Well-structured markdown with clear heading hierarchy (primary)
- CSS, shell scripts, config files (reference material — fixed chunking)
- Python skeleton output from skeleton_reader (already structured)

**Not in scope for v0.1:**
- Unstructured prose
- PDFs
- Binary files

---

## Backend: Ollama + sqlite-vec

ragkit uses Ollama for embeddings — the same runtime already used for
LLM generation in designing-gemma. This keeps the stack coherent and
enables a future experiment axis: same document collection, different
embedding models, does retrieval change?

The default embedding model is `nomic-embed-text`, which Ollama serves
the same way it serves chat models.

The index is a single SQLite database file, extended with `sqlite-vec`
for vector similarity search. One `.db` file per index — inspectable
with any SQLite client, queryable ad-hoc, no server required.

**Dependencies:**
- `sqlite-vec` — vector similarity search extension for SQLite
- `httpx` — Ollama embedding API calls (async-capable, modern)
- `pyyaml` — config parsing

No other new dependencies.

---

## Directory Structure

```
dev-utils/python/ragkit/
├── pyproject.toml
├── README.md
├── src/
│   └── ragkit/
│       ├── __init__.py
│       ├── chunker.py          ← document chunking strategies
│       ├── embedder.py         ← Ollama embedding calls
│       ├── index.py            ← SQLite index build and query
│       └── cli.py              ← CLI entry points
└── tests/
    ├── __init__.py
    ├── test_chunker.py
    ├── test_embedder.py
    └── test_index.py
```

---

## pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ragkit"
version = "0.1.0"
description = "Local RAG index builder and retriever for structured documents"
authors = [
    { name = "Carolyn Boyle" }
]
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "sqlite-vec>=0.1.0",
    "httpx>=0.27",
    "pyyaml>=6.0",
]

[project.scripts]
ragkit-build = "ragkit.cli:build"
ragkit-query = "ragkit.cli:query"

[tool.setuptools.packages.find]
where = ["src"]
include = ["ragkit*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

## Chunking Strategy

### Markdown documents

Split on heading boundaries (`#`, `##`, `###`). Each chunk is one
logical section — the heading text plus its body content.

**Heading hierarchy is preserved** by prepending the full ancestor
path to every chunk. A chunk that lives under `## Configuration > ### Auth`
carries that context string, so retrieved chunks are self-contained even
when read in isolation.

**Character ceiling:** 2,000 characters per chunk (configurable). A
section that exceeds the ceiling is split on paragraph boundaries
(`\n\n`). The ancestor heading is prepended to each sub-chunk.

This handles the one realistic failure mode (long sections with no
subheadings) without needing a full second strategy.

### CSS, shell scripts, config files

Fixed-size chunking: 800 characters per chunk, 80-character overlap.
These are reference material — structure is less important than
coverage. Overlap prevents relevant content from being split at
a boundary.

### Python skeleton output

Accepts skeleton data (as produced by skeleton_reader) directly.
Each function or class is one chunk. No re-parsing of source files.
ragkit consumes the same structured output designing-gemma already
produces.

---

## SQLite Schema

```sql
-- ragkit index schema

CREATE TABLE documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,          -- original file path
    doc_type    TEXT NOT NULL,          -- 'markdown', 'css', 'skeleton'
    indexed_at  TEXT NOT NULL           -- ISO timestamp
);

CREATE TABLE chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    chunk_index INTEGER NOT NULL,       -- position within document
    heading     TEXT,                   -- ancestor heading path, if any
    content     TEXT NOT NULL,          -- raw chunk text
    char_count  INTEGER NOT NULL
);

-- sqlite-vec virtual table — one row per chunk
CREATE VIRTUAL TABLE chunk_vectors USING vec0(
    chunk_id    INTEGER PRIMARY KEY,
    embedding   FLOAT[768]              -- nomic-embed-text output dimension
);
```

The `chunks` table holds human-readable content. The `chunk_vectors`
virtual table holds the embeddings. They join on `chunk_id = chunks.id`.
This separation means you can inspect chunks as plain text without
touching the vector store.

---

## Module: `chunker.py`

```
chunk_markdown(text, source_path, max_chars=2000) -> list[dict]
chunk_fixed(text, source_path, size=800, overlap=80) -> list[dict]
chunk_skeleton(skeleton_data, source_path) -> list[dict]
```

Each returns a list of chunk dicts:

```python
{
    "source_path": str,
    "heading":     str | None,   # ancestor path, e.g. "## Config > ### Auth"
    "content":     str,
    "char_count":  int,
}
```

chunker.py has no external dependencies — stdlib only. It is the most
testable module in ragkit and should have the most thorough tests.

---

## Module: `embedder.py`

```
embed(text, model, ollama_url) -> list[float]
embed_batch(texts, model, ollama_url) -> list[list[float]]
```

Calls the Ollama `/api/embed` endpoint. Returns raw float vectors.
Raises `EmbedderError` on connection failure or unexpected response.

`embed_batch` sends texts one at a time and collects results — Ollama's
embed endpoint accepts a single string, not a list. Batching here means
"loop and collect" not "single API call."

Default model: `nomic-embed-text`. Overridable per index config.

---

## Module: `index.py`

### Building an index

```
build_index(
    docs_dir,          # path to document folder
    index_path,        # path to write .db file
    config,            # dict from ragkit config block
) -> BuildResult
```

Walk `docs_dir`, detect file type, chunk appropriately, embed each
chunk, write to SQLite. Idempotent — rebuilding replaces the existing
index cleanly.

`BuildResult`:
```python
{
    "documents":  int,   # files indexed
    "chunks":     int,   # total chunks written
    "skipped":    list,  # files skipped with reasons
    "index_path": str,
}
```

### Querying an index

```
query_index(
    query_text,        # the prompt or a summary of it
    index_path,        # path to .db file
    config,            # dict — top_k, model, ollama_url
) -> list[ChunkResult]
```

Embed the query, run cosine similarity against `chunk_vectors`, return
top-k chunks as a ranked list.

`ChunkResult`:
```python
{
    "source_path": str,
    "heading":     str | None,
    "content":     str,
    "score":       float,        # cosine similarity 0.0–1.0
    "rank":        int,
}
```

---

## CLI Entry Points

### `ragkit-build`

```bash
ragkit-build --docs-dir ./docs --index ./ragkit.db --model nomic-embed-text
```

Builds or rebuilds the index. Prints a summary on completion:

```
Indexed 12 documents → 47 chunks
Skipped: requirements.txt (no chunking strategy for .txt)
Index written: ./ragkit.db
```

### `ragkit-query`

```bash
ragkit-query --index ./ragkit.db --query "write a script following project rules" --top-k 5
```

Returns ranked chunks to stdout. Useful for debugging retrieval before
running an experiment.

```
[1] coding_rules.md > ## Naming Conventions  (score: 0.91)
[2] project_rules.md > ## Script Requirements  (score: 0.87)
...
```

---

## Integration with designing-gemma

### Experiment config

A new `local_docs:` key sits alongside `repo_read:` in experiment YAML:

```yaml
local_docs:
  index: /path/to/ragkit.db         # pre-built index
  query: "{{ prompt_label }}"        # what to retrieve against
  top_k: 5                           # chunks to inject
  min_score: 0.6                     # ignore low-confidence results
```

### Runner behaviour

1. Load `local_docs:` config block
2. Call `ragkit.index.query_index()` with the prompt label as query
3. Format retrieved chunks as `{{ local_docs }}` template variable
4. Write retrieved chunk list to `local_docs_latest.txt` in results dir
   (same pattern as `context_latest.txt`) — fully reproducible

### Prompt template variable

Retrieved chunks are formatted as a numbered block:

```
[1] source: coding_rules.md — Naming Conventions
    ...chunk content...

[2] source: project_rules.md — Script Requirements
    ...chunk content...
```

Injected as `{{ local_docs }}` alongside `{{ repo_context }}`.

---

## Logging and Reproducibility

Every run writes `local_docs_latest.txt` to the results directory:

```
# local_docs_latest.txt — ragkit retrieval snapshot
# Generated : 2026-05-27T14:32:01
# Index     : /path/to/ragkit.db
# Query     : "write a script following project rules"
# Top-K     : 5
# Min Score : 0.6
# Retrieved : 4 chunks (1 below min_score, excluded)
#
[1] source: coding_rules.md ...
```

This makes retrieval fully inspectable and reproducible — the same
pattern established by `context_latest.txt` for repo context.

---

## Exception Handling

| Exception | Raised by | Meaning |
|---|---|---|
| `RagkitConfigError` | index.py, cli.py | Bad or missing config |
| `EmbedderError` | embedder.py | Ollama unreachable or bad response |
| `IndexError` | index.py | Index file missing, corrupt, or schema mismatch |
| `ChunkerError` | chunker.py | Document could not be chunked |

The designing-gemma runner catches `RagkitConfigError` and `IndexError`
and prints a clear error message — same pattern as `RepoReaderError`.

---

## Testing Requirements

Per project rules: unit tests are required, not optional.

### `test_chunker.py`
- Markdown with clear headings → correct chunk boundaries
- Markdown with a long section (no subheadings) → ceiling applied, sub-chunks produced
- Markdown with no headings → falls back to fixed chunking
- Fixed chunking → correct overlap
- Skeleton data → one chunk per function/class
- Empty document → returns empty list, no error

### `test_embedder.py`
- Valid text → returns list of floats, correct length
- Ollama unreachable → raises `EmbedderError`
- Empty string → raises `EmbedderError` or returns zero vector (document expected behaviour)

### `test_index.py`
- Build on empty dir → BuildResult with 0 documents
- Build with mixed file types → correct chunking strategy applied per type
- Rebuild → replaces existing index cleanly (no duplicate rows)
- Query against known index → top result matches expected source
- Query with `min_score` → low-confidence chunks excluded
- Missing index file → raises `IndexError`

---

## Future / Out of Scope for v0.1

- Non-Ollama embedding backends (sentence-transformers, OpenAI-compatible)
- Incremental index updates (only re-index changed files)
- Multiple index support in a single experiment
- Chunk size configured per file type in experiment YAML
- The Obsidian vault (deliberately excluded — structure requirement not met)

---

## Commit Message (after implementation)

```
feat: add ragkit — local RAG index builder and retriever
```

---

## Part of Project Crew

ragkit is one tool in the dev-utils / Project Crew ecosystem:

- **doc-gen** — filesystem manifest generator
- **fletcher** — GitHub URL manifest generator
- **treekit** — directory tree scaffolding from markdown
- **setupkit** — plugin lifecycle manager
- **menukit** — YAML-driven menu library
- **dbkit** — PostgreSQL/SQLite abstraction layer
- **viewkit** — YAML-driven SQL query and view builder
- **sniffkit** — content-type detector and file classifier
- **imagekit** — image encoding utilities
- **ragkit** — local RAG index builder and retriever ← this

---

## Author

Carolyn Boyle

---

## License

MIT
