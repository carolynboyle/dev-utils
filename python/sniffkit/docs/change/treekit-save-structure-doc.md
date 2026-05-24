# Changeset: Auto-create docs/project_structure.md
## treekit

**Status:** Pending implementation  
**Scope:** `builder.py`, `cli.py`  
**Size:** Small refactor

---

## What

After a successful build, treekit copies the input markdown file to
`<root>/docs/project_structure.md`, creating `docs/` if it was not
included in the tree definition.

---

## Why

Every project built with treekit should have a record of its own
scaffolding in a predictable location. Without this, the input file
is wherever the user happened to put it — or gone entirely if they
didn't think to keep it.

---

## Behaviour

- `docs/` created if not already present (no error if it was in the tree)
- Input file copied to `docs/project_structure.md` after build completes
- If input came from stdin, skip silently — no source file to copy
- Dry run: note the action in output but write nothing
- Log entry includes the destination path

---

## Changes

### `builder.py`

Add a `_save_structure_doc(source: Path, root: Path)` method to
`TreeBuilder`. Called at the end of `build()` on success only.

```python
def _save_structure_doc(self, source: Path | None, root: Path) -> None:
    """
    Copy the input markdown to <root>/docs/project_structure.md.
    Creates docs/ if it does not exist.
    Skips silently if source is None (stdin input).
    """
    if source is None:
        return
    docs_dir = root / "docs"
    docs_dir.mkdir(exist_ok=True)
    dest = docs_dir / "project_structure.md"
    if not self.dry_run:
        shutil.copy2(source, dest)
```

### `cli.py`

Pass the resolved input path through to `TreeBuilder` so it has access
to the source file. Currently the CLI reads the file contents and passes
text only — the path needs to be passed alongside or stored on the builder.

### Dry run output addition

```
Would create:
  ...
  (existing tree items)
  ...

Post-build:
  docs/project_structure.md  ← copied from input file
```

---

## Commit Message

```
feat: auto-save input file as docs/project_structure.md after build
```
