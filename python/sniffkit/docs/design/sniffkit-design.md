# sniffkit — Design Document

**Location:** `dev-utils/python/sniffkit/`  
**Version:** 0.1.0  
**Status:** Pre-implementation design — approved before coding begins  
**Part of:** Project Crew / dev-utils ecosystem

---

## Purpose

sniffkit reads `.txt` files, detects their content type by heuristic
analysis, and copies them to a target directory with the correct file
extension. Files that cannot be classified with sufficient confidence
are skipped and reported.

Primary consumer: designing-gemma, where experiment output files are
written as `.txt` regardless of content. sniffkit makes them usable
as HTML, CSS, Markdown, etc. without manual inspection.

General enough to be useful anywhere raw LLM output or unknown text
files need to be sorted by content type.

---

## Tagline

*"for when you need to know what's in the bag"*

---

## Directory Structure

```
dev-utils/python/sniffkit/
├── pyproject.toml
├── src/
│   └── sniffkit/
│       ├── __init__.py
│       ├── classifier.py          ← ResultClassifier class + CLI entry point
│       └── detectors/
│           ├── __init__.py        ← Detector protocol + @register decorator
│           ├── css_detector.py
│           ├── html_detector.py
│           ├── json_detector.py
│           ├── md_detector.py
│           └── sql_detector.py
└── tests/
    ├── __init__.py
    ├── test_classifier.py
    └── test_detectors.py
```

---

## pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "sniffkit"
version = "0.1.0"
description = "Content-type detector and file classifier for raw text output"
authors = [
    { name = "Carolyn Boyle" }
]
readme = "README.md"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
sniffkit = "sniffkit.classifier:main"

[tool.setuptools.packages.find]
where = ["src"]
include = ["sniffkit*"]
```

No third-party dependencies. All detection is stdlib only — `re`, `json`,
`pathlib`. This is intentional; sniffkit should install anywhere Python 3.11
runs with zero friction.

---

## Module: `detectors/__init__.py`

The registry and protocol live here. Every detector imports from this
module. `ResultClassifier` imports from this module. Neither side knows
the other exists directly.

### The `Detector` Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Detector(Protocol):
    """
    Protocol that every sniffkit detector must satisfy.

    A detector examines raw text and returns a confidence score
    between 0.0 (definitely not this type) and 1.0 (certain match).
    It does not modify the text or perform any I/O.
    """

    #: Short lowercase label used in CLI flags and output filenames.
    #: Examples: "html", "css", "md", "json", "sql"
    type_label: str

    #: File extension to use when copying/renaming.
    #: Includes the dot: ".html", ".css", ".md"
    extension: str

    def detect(self, text: str) -> float:
        """
        Analyse text and return a confidence score.

        Args:
            text: Full file contents as a string.

        Returns:
            Float in range [0.0, 1.0].
            0.0 = definitely not this type.
            1.0 = certain match.
            Scores >= min_confidence threshold are accepted.
        """
        ...
```

### The Registry

```python
_REGISTRY: dict[str, Detector] = {}

def register(detector: Detector) -> Detector:
    """
    Decorator that adds a detector instance to the registry.

    Usage:
        @register
        class CssDetector:
            type_label = "css"
            extension  = ".css"

            def detect(self, text: str) -> float:
                ...

    The class is registered under its type_label. Duplicate labels
    raise a ValueError at import time — fail loud, fail early.
    """
    if detector.type_label in _REGISTRY:
        raise ValueError(
            f"Detector conflict: '{detector.type_label}' is already registered. "
            f"Each type_label must be unique."
        )
    _REGISTRY[detector.type_label] = detector
    return detector


def get_registry() -> dict[str, Detector]:
    """Return a copy of the current detector registry."""
    return dict(_REGISTRY)
```

### Auto-import

The `__init__.py` imports all detector modules so their `@register`
decorators fire at package import time. Adding a new detector is:
1. Create the file
2. Add the import here

```python
# Auto-import all detectors to trigger @register
from sniffkit.detectors import (  # noqa: F401
    css_detector,
    html_detector,
    json_detector,
    md_detector,
    sql_detector,
)
```

---

## Detector Specification

Each detector follows the same pattern. `css_detector.py` is the
canonical example — implement all others identically.

### `css_detector.py` — Fully Worked Example

```python
"""
CSS content detector for sniffkit.

Scores text on the density and variety of CSS-specific syntax patterns.
Does not attempt to parse CSS — uses regex signal counting only.
"""

import re
from sniffkit.detectors import register, Detector


@register
class CssDetector:
    """Detects CSS content by heuristic pattern analysis."""

    type_label: str = "css"
    extension:  str = ".css"

    # Patterns that strongly suggest CSS
    _STRONG_SIGNALS = [
        re.compile(r'\{[^}]*\}'),              # rule blocks
        re.compile(r'@media\b'),               # media queries
        re.compile(r'@keyframes\b'),           # animations
        re.compile(r'@import\b'),              # imports
        re.compile(r':\s*(hover|focus|active|root|before|after)\b'),  # pseudo
    ]

    # Patterns that suggest CSS but also appear in other formats
    _WEAK_SIGNALS = [
        re.compile(r'[a-z-]+\s*:\s*[^;{}\n]+;'),  # property: value;
        re.compile(r'^\s*\.[a-z][\w-]*\s*\{', re.MULTILINE),   # .class {
        re.compile(r'^\s*#[a-z][\w-]*\s*\{', re.MULTILINE),    # #id {
        re.compile(r'^\s*[a-z][\w-]*\s*\{', re.MULTILINE),     # element {
    ]

    # Patterns that indicate this is NOT css
    _NEGATIVE_SIGNALS = [
        re.compile(r'<!DOCTYPE', re.IGNORECASE),
        re.compile(r'<html', re.IGNORECASE),
        re.compile(r'^\s*#{1,6}\s+\w', re.MULTILINE),   # markdown headings
        re.compile(r'SELECT\s+\w', re.IGNORECASE),
    ]

    def detect(self, text: str) -> float:
        """Return confidence score for CSS content."""
        if not text or not text.strip():
            return 0.0

        # Immediate disqualification
        for pattern in self._NEGATIVE_SIGNALS:
            if pattern.search(text):
                return 0.0

        score = 0.0

        # Strong signals: 0.25 each, capped at 0.50
        strong_hits = sum(
            1 for p in self._STRONG_SIGNALS if p.search(text)
        )
        score += min(strong_hits * 0.25, 0.50)

        # Weak signals: 0.10 each, capped at 0.40
        weak_hits = sum(
            1 for p in self._WEAK_SIGNALS if p.search(text)
        )
        score += min(weak_hits * 0.10, 0.40)

        # Density bonus: if { and } appear frequently relative to line count
        lines = text.splitlines()
        if lines:
            brace_lines = sum(1 for line in lines if '{' in line or '}' in line)
            density = brace_lines / len(lines)
            if density > 0.15:
                score += 0.10

        return min(score, 1.0)
```

### Detector Scoring Guidelines

All detectors follow the same scoring shape:

| Signal type | Per hit | Cap |
|---|---|---|
| Strong (type-unique syntax) | +0.25 | 0.50 |
| Weak (common but suggestive) | +0.10 | 0.40 |
| Density/structural bonus | +0.10 | 0.10 |
| Negative (disqualifying) | → 0.0 immediately | — |

Maximum possible score: 1.0. Minimum to be accepted: `min_confidence`
(default 0.6, configurable via CLI flag).

---

## Detector Signals Reference

Implementation notes for the remaining four detectors.

### `html_detector.py`

**Strong signals:**
- `<!DOCTYPE html` (case-insensitive)
- `<html` tag
- `<head>` + `<body>` both present
- `<div`, `<span`, `<p>`, `<a href` — any two or more

**Weak signals:**
- Any `<tag>` pattern
- `</tag>` closing tags
- `class="..."` or `id="..."` attributes

**Negative signals:**
- High density of `{` / `}` without surrounding tags (likely CSS)
- `# Heading` at line start (likely Markdown)
- `SELECT` / `INSERT` / `CREATE TABLE` (likely SQL)

### `md_detector.py`

**Strong signals:**
- `# ` or `## ` at line start (ATX headings)
- `---` or `===` underline headings
- Fenced code blocks (` ``` ` or `~~~`)
- `[text](url)` link syntax

**Weak signals:**
- `**bold**` or `*italic*`
- `- ` or `* ` list items at line start
- `> ` blockquotes
- `| col |` table rows

**Negative signals:**
- `<!DOCTYPE` or `<html` (HTML)
- High `{` / `}` density (CSS)

### `json_detector.py`

**Strategy:** attempt `json.loads()` on the stripped text first.
If it succeeds and the result is a dict or list → score 1.0.
If it raises, fall through to heuristic scoring.

**Strong signals (heuristic fallback):**
- Starts with `{` or `[`
- Contains `": "` key-value patterns
- Ends with `}` or `]`

**Negative signals:**
- `<!DOCTYPE`, `<html`, `SELECT`

**Note:** JSON detection should be tried early. A valid JSON parse
is unambiguous; no other detector should score above it for clean JSON.

### `sql_detector.py`

**Strong signals:**
- `SELECT ... FROM` pattern
- `CREATE TABLE` / `CREATE INDEX`
- `INSERT INTO`
- `DROP TABLE` / `ALTER TABLE`

**Weak signals:**
- `WHERE`, `JOIN`, `GROUP BY`, `ORDER BY` keywords
- `--` line comments
- `;` statement terminators at line end

**Negative signals:**
- `<!DOCTYPE`, `<html`
- `{` / `}` brace density (CSS)

---

## Module: `classifier.py`

### `ClassificationResult` dataclass

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ClassificationResult:
    source_path: Path          # original .txt file
    dest_path: Path | None     # where the file was/would be copied
    type_label: str | None     # winning detector label, or None
    confidence: float          # winning score, or 0.0
    skipped: bool              # True if below threshold or uncertain
    dry_run: bool              # True if no files were actually written
    error: str | None          # error message if something went wrong
```

### `ResultClassifier` class

```python
class ResultClassifier:
    """
    Walks a directory tree, classifies .txt files by content type,
    and copies them to a target directory with the correct extension.
    """

    def __init__(
        self,
        min_confidence: float = 0.6,
        target_types: list[str] | None = None,
        verbose: bool = False,
    ):
        """
        Args:
            min_confidence: Minimum score to accept a classification.
            target_types:   If provided, only run detectors for these
                            type labels. All others are skipped entirely.
            verbose:        If True, emit per-file reasoning to stdout.
        """

    def classify_file(self, path: Path) -> ClassificationResult:
        """
        Classify a single file.

        Runs only the detectors matching target_types (or all detectors
        if target_types is None). Returns the highest-confidence result
        above min_confidence, or a skipped result if none qualify.

        Args:
            path: Path to a .txt file.

        Returns:
            ClassificationResult — always returns, never raises.
            Errors are captured in result.error.
        """

    def process_results(
        self,
        results_dir: Path,
        output_dir: Path,
        dry_run: bool = True,
    ) -> list[ClassificationResult]:
        """
        Walk results_dir recursively, classify every .txt file found,
        and copy classified files to output_dir preserving the filename
        with the new extension.

        Original .txt files are never modified or deleted.

        Args:
            results_dir: Root directory to walk (searches recursively).
            output_dir:  Destination for classified files.
            dry_run:     If True, compute results but write nothing.

        Returns:
            List of ClassificationResult for every .txt file encountered.
        """
```

### Confidence tie-breaking

If two detectors score above `min_confidence`, the higher score wins.
If scores are equal, the first detector in registry insertion order wins
(insertion order is deterministic — alphabetical by filename, since
`detectors/__init__.py` imports them in that order).

---

## CLI Specification

Entry point: `sniffkit` (via `pyproject.toml` `[project.scripts]`)

```
sniffkit [OPTIONS]

Options:
  --results-dir PATH        Root directory to walk for .txt files.
                            Default: current working directory.

  --output-dir PATH         Where to copy classified files.
                            Required unless --dry-run is set.

  --target-types TYPE...    One or more type labels to detect.
                            Only these detectors run; all others skipped.
                            Examples: --target-types css
                                      --target-types html css md
                            Default: all registered detectors.

  --dry-run                 Compute and display results. Write nothing.
                            Safe to run without --output-dir.

  --min-confidence FLOAT    Minimum confidence score to accept.
                            Range: 0.0–1.0. Default: 0.6

  --verbose                 Show per-file detector scores and reasoning.

  --list-detectors          Print all registered detector labels and
                            extensions, then exit. Useful for debugging
                            and verifying registration.
```

### Example invocations

```bash
# Dry run — see what would be classified as CSS
sniffkit --results-dir experiments/ --target-types css --dry-run

# Classify all HTML and CSS, copy to web/static/
sniffkit \
  --results-dir experiments/ \
  --target-types html css \
  --output-dir web/app/static/classified/ \
  --min-confidence 0.7

# See what detectors are loaded
sniffkit --list-detectors

# Verbose dry run — see scoring reasoning per file
sniffkit --results-dir experiments/ --dry-run --verbose
```

### CLI output format

```
sniffkit — scanning experiments/ for [css]

  run_042_gemma4-e2b_settings_page.txt  →  css  (0.85)  →  run_042_gemma4-e2b_settings_page.css
  run_043_gemma4-e4b_settings_page.txt  →  css  (0.72)  →  run_043_gemma4-e4b_settings_page.css
  run_044_gemma4-e2b_readme_gen.txt     →  ?    (0.41)  →  skipped (below threshold)
  run_045_gemma4-e4b_theme_choice.txt   →  ?    (0.00)  →  skipped (uncertain)

Summary: 2 classified, 2 skipped, 0 errors
Destination: web/app/static/classified/
```

Verbose adds a block per file showing each detector's score before the
winner is selected.

---

## Wiring into designing-gemma

Install sniffkit as an editable dependency in designing-gemma's venv:

```bash
pip install -e ~/projects/dev-utils/python/sniffkit
```

Add to `requirements.txt` or `pyproject.toml` dependencies as a local
path reference for the container build.

Import in designing-gemma:

```python
from sniffkit.classifier import ResultClassifier, ClassificationResult

classifier = ResultClassifier(
    min_confidence=0.65,
    target_types=["html", "css"],
    verbose=False,
)

results = classifier.process_results(
    results_dir=Path("experiments/"),
    output_dir=Path("web/app/static/classified/"),
    dry_run=False,
)

for r in results:
    if not r.skipped:
        print(f"  {r.source_path.name} → {r.type_label} → {r.dest_path.name}")
```

The Flask web UI (future) will call `process_results()` via a thin
route wrapper and stream results back as JSON.

---

## Testing Requirements

Per project rules: unit tests are required, not optional. New
functionality is not done until it has tests.

### `test_detectors.py`

For each detector, test:
- Canonical positive example → score >= 0.6
- Canonical negative example → score == 0.0
- Empty string → score == 0.0
- Ambiguous content → score < 0.6 (documents expected behavior)
- Negative signal presence → score == 0.0 immediately

### `test_classifier.py`

- `classify_file()` returns correct type for known files
- `classify_file()` returns `skipped=True` for ambiguous files
- `target_types` filter prevents non-target detectors from running
- `dry_run=True` produces results but creates no files
- `dry_run=False` copies files with correct extension
- Original `.txt` files are never modified

---

## Exception Handling

sniffkit never raises to the caller from `classify_file()` or
`process_results()`. All errors are captured in `ClassificationResult.error`.

The CLI reports errors per-file in output and includes them in the
summary count. Exit code:

| Code | Meaning |
|---|---|
| `0` | Completed — even if some files were skipped or had errors |
| `1` | Fatal error before processing began (bad args, unreadable dir) |

---

## Commit Message (after implementation)

```
feat: add sniffkit — content-type detector and file classifier
```

---

## Part of Project Crew

sniffkit is one tool in the dev-utils / Project Crew ecosystem:

- **doc-gen** — filesystem manifest generator
- **fletcher** — GitHub URL manifest generator
- **treekit** — directory tree scaffolding from markdown
- **setupkit** — plugin lifecycle manager
- **menukit** — YAML-driven menu library
- **dbkit** — PostgreSQL/SQLite abstraction layer
- **viewkit** — YAML-driven SQL query and view builder
- **sniffkit** — content-type detector and file classifier ← this

---

## Author

Carolyn Boyle

---

## License

MIT
