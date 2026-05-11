# Dev-Utils Repo Standardization: What Breaks and Why

## Background

The `dev-utils` repo is a collection of composable Python CLI tools and utilities
built around a config-over-code, Unix-composability philosophy. As the ecosystem
has grown, packages have accumulated inconsistencies: some use src layout, some
don't; some have READMEs, some don't; a couple of utility scripts have no home at
all. The goal of this standardization pass is to bring everything into alignment
before the repo goes public.

The task is being delegated to an AI coding agent (Gemma). Before handing it off,
a pre-flight analysis was done to identify every file that will break if the
restructure is done naively — and to define the rules for doing it safely.

---

## Current State of the Repo

### Already correct (src layout)
- `contactkit`
- `todo`
- `setupkit`

### Flat layout — need conversion to src
These have the antipattern `pkgname/pkgname/` instead of `pkgname/src/pkgname/`:
- `dbkit`
- `fletcher`
- `viewkit`

### Loose files with no package home
- `python/cli_utils.py`
- `python/display_utils.py`
- `python/viewkit/cli.py` — sits in the viewkit folder root, outside the package
- `python/viewkit/runner.py` — same

### Bash scripts
- `bash/connection_tools/tmux-launch.sh` — has a folder, no README
- `bash/container_tools/docker-python-builder.sh` — has a folder, no README

### Missing READMEs
`dbkit`, `fletcher`, `setupkit`, both bash tool folders

---

## What Actually Breaks When You Move Things

### 1. The src layout conversion (highest risk)

When a Python package is installed editable (`pip install -e .`), the import
system resolves package location from `pyproject.toml`. Moving source files
without updating `pyproject.toml` breaks every import of that package immediately,
on every machine that has it installed.

Specifically, `[tool.setuptools.packages.find]` must gain `where = ["src"]` as
part of the same commit that moves the files.

All three flat-layout packages also have stale `.egg-info` directories at the old
location. After conversion, these must be deleted and the package reinstalled.
This is a **manual step** — the agent cannot reach into running environments.

### 2. The setupkit plugin YAML files (often overlooked)

Each package has a plugin configuration file in `~/.config/dev-utils/setupkit/`.
These files contain a `path_prefix` key that points directly into the package
directory tree:

```yaml
# dbkit.yaml — BEFORE conversion
path_prefix: python/dbkit/dbkit/

# dbkit.yaml — AFTER conversion
path_prefix: python/dbkit/src/dbkit/
```

If these are not updated atomically with the repo restructure, setupkit will be
pointing at paths that no longer exist. The install URLs (`git+https://...`) are
not affected — pip resolves those from `pyproject.toml` — but anything that reads
`path_prefix` to locate package files will fail silently or noisily depending on
context.

Affected files:
- `~/.config/dev-utils/setupkit/dbkit.yaml`
- `~/.config/dev-utils/setupkit/fletcher.yaml`
- `~/.config/dev-utils/setupkit/viewkit.yaml`
- `~/.config/dev-utils/setupkit/menukit.yaml` (menukit is not yet in the manifest
  — a separate issue to address)

### 3. The loose files

`cli_utils.py` and `display_utils.py` are sitting bare in the `python/` directory.
If anything imports them, it is doing so because that directory is on the path.
Moving them into a proper package changes the import path.

**The agent must check for importers before touching these files, not move them
speculatively.**

`viewkit/cli.py` and `viewkit/runner.py` are outside the `viewkit/viewkit/`
package directory but inside the viewkit folder. If they are invoked as scripts
they can be moved freely. If anything imports them relative to their current
location, that breaks. The `pyproject.toml` entry points are the thing to check.

### 4. Version consistency

Both `pyproject.toml` and the setupkit YAML carry a `version` field. These can
drift independently today. A structural change like flat→src warrants a **minor
version bump** (e.g. `0.1.0 → 0.2.0`), not a patch bump — it is a breaking
change from a packaging standpoint. Both files must be updated to the same version
as part of the same commit.

Packages receiving only README additions: patch bump or no bump. New packages
being created from loose files: start at `0.1.0`.

---

## Rules for the Agent

These constraints were defined specifically to prevent the restructure from
creating cascading breakage across the environment:

**Do one package at a time.** Not all three flat-layout conversions in a single
pass. Each conversion is a discrete, testable unit of work.

**Each package conversion must touch these files in the same commit:**
1. Move source files to `src/pkgname/`
2. Update `pyproject.toml` — add `where = ["src"]`
3. Update `~/.config/dev-utils/setupkit/<package>.yaml` — update `path_prefix`
4. Bump version consistently in both files

**Do not delete `.egg-info` directories.** Flag them for manual cleanup. Deleting
them prematurely masks whether the reinstall actually succeeded.

**Stop after each package and wait.** The human must run `pip install -e .` on
every affected machine before the agent proceeds to the next package.

**For loose files: identify importers first.** Do not move `cli_utils.py` or
`display_utils.py` until it is confirmed what (if anything) imports them.

**Safe to do in parallel, no waiting required:**
- Add READMEs to bash tool folders
- Add READMEs to packages not being restructured

---

## The Broader Lesson

The breakage surface here was larger than it first appeared, because the repo has
multiple consumers of its internal structure:

- The Python import system (via editable installs)
- The packaging system (via `.egg-info`)
- A separate configuration system (`setupkit` plugin YAMLs) that duplicates
  structural information

Any one of these, updated without the others, produces a broken environment. The
pre-flight analysis existed to map all three before the first file moved.

This is also why the version fields in `pyproject.toml` and the setupkit YAMLs
being out of sync is a future problem waiting to happen — the single source of
truth principle applies to version numbers as much as to code.

---

## Files Changed Per Package (Summary Table)

| File | dbkit | fletcher | viewkit |
|------|-------|----------|---------|
| Source tree moved to `src/` | ✓ | ✓ | ✓ |
| `pyproject.toml` updated | ✓ | ✓ | ✓ |
| setupkit YAML `path_prefix` updated | ✓ | ✓ | ✓ |
| Version bumped (both files) | ✓ | ✓ | ✓ |
| `.egg-info` flagged for manual cleanup | ✓ | ✓ | ✓ |
| Manual reinstall required | ✓ | ✓ | ✓ |
