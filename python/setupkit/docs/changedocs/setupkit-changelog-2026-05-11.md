# setupkit changelog — 2026-05-11

## Summary

Four changes to setupkit and related packages:

1. `initialize.py` — registry-driven init, correct pip URL format, master→main fix
2. `pyproject.toml` — added package-data entry for data/*.yaml
3. `data/setupkit.yaml` — was untracked in git, now committed
4. `python/menukit/pyproject.toml` — wrong build backend corrected

Plus two new root-level files: `setupkit-registry.yaml` and updated `setup.sh`.

---

## 1. `python/setupkit/src/setupkit/initialize.py`

### Problem

`setupkit init <name>` prompted interactively for every config value
(manifest URL, path prefix, pyproject path, install URL) even though
all values are fully derivable from the repo structure. On a public
repo with a consistent layout this was unnecessary friction.

Additionally, install URLs were generated in the format:

```
git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/<name>
```

Newer pip requires the package name prefix:

```
<name> @ git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/<name>
```

The interactive fallback also constructed manifest URLs using
`/raw/master/` instead of `/raw/main/`.

### Changes

**`init_plugin()`** — now tries registry path first, falls back to
interactive only if registry unavailable or package not listed.

**BEFORE:**
```python
def init_plugin(name: str) -> None:
    print(f"\nsetupkit init — configuring plugin: {name}")
    print("=" * 50)

    # Step 1 — manifest URL
    manifest_url = _prompt_manifest_url(name)
    ...
```

**AFTER:**
```python
def init_plugin(name: str) -> None:
    print(f"\nsetupkit init — configuring plugin: {name}")
    print("=" * 50)

    registry = _load_registry()

    if registry and name in registry.get("packages", {}):
        _init_from_registry(name, registry)
    else:
        if registry and name not in registry.get("packages", {}):
            print(f"\nWarning: {name!r} not found in registry — falling back to interactive mode.")
        _init_interactive(name)
```

**New: `_init_from_registry()`** — derives all config values from registry entry:

```python
def _init_from_registry(name: str, registry: dict) -> None:
    repo   = registry["repo"]
    branch = registry["branch"]
    manifest_path = registry["manifest"]
    entry  = registry["packages"][name]
    path   = entry["path"]

    manifest_url = f"{repo}/raw/{branch}/{manifest_path}"
    pyproject    = f"{path}/pyproject.toml"
    path_prefix  = f"{path}/src/{name}/"
    install_url  = f"{name} @ git+{repo}.git#subdirectory={path}"
    ...
```

**New: `_load_registry()`** — fetches `setupkit-registry.yaml` from
upstream repo via git remote detection, falls back to local file search:

```python
def _load_registry() -> Optional[dict]:
    repo_url = _detect_git_repo()
    if repo_url:
        registry_url = f"{repo_url}/raw/main/{_REGISTRY_FILENAME}"
        try:
            response = requests.get(registry_url, timeout=10)
            response.raise_for_status()
            data = yaml.safe_load(response.text)
            if isinstance(data, dict) and "packages" in data:
                return data
        except (requests.RequestException, yaml.YAMLError):
            pass
    # Falls back to local file search...
```

**`_prompt_manifest_url()` fix** — `master` → `main`:

**BEFORE:**
```python
default_url = f"{detected}/raw/master/.doc-gen/manifest.fletch"
```

**AFTER:**
```python
default_url = f"{detected}/raw/main/.doc-gen/manifest.fletch"
```

**`_prompt_install_url()` fix** — added `name @` prefix:

**BEFORE:**
```python
default = f"git+{repo}.git#subdirectory=python/{name}"
```

**AFTER:**
```python
default = f"{name} @ git+{repo}.git#subdirectory=python/{name}"
```

---

## 2. `python/setupkit/pyproject.toml`

### Problem

`data/setupkit.yaml` was not included when installing setupkit from
the repo (non-editable install). The package installed successfully
but crashed immediately on first use with:

```
FileNotFoundError: .../setupkit/data/setupkit.yaml
```

### Change

Added `[tool.setuptools.package-data]` section.

**BEFORE:**
```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["setupkit*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**AFTER:**
```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["setupkit*"]

[tool.setuptools.package-data]
setupkit = ["data/*.yaml"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Why:** `package-data` tells setuptools to include non-Python files
in the built package. Without it, `data/setupkit.yaml` exists in the
source tree but is not copied into the installed package.

---

## 3. `python/setupkit/src/setupkit/data/setupkit.yaml`

### Problem

File existed on disk but had never been committed to git. Was invisible
to any machine installing setupkit from the repo.

### Change

File added to git tracking. No content change.

```bash
git add python/setupkit/src/setupkit/data/setupkit.yaml
```

---

## 4. `python/menukit/pyproject.toml`

### Problem

Build backend was set to `setuptools.backends.legacy:build` which does
not exist in the version of setuptools available in the tools venv.
Installing menukit failed with:

```
BackendUnavailable: Cannot import 'setuptools.backends.legacy'
```

### Change

**BEFORE:**
```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"
```

**AFTER:**
```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
```

**Why:** `setuptools.backends.legacy` was introduced in setuptools 69+.
The standard `setuptools.build_meta` backend works across all supported
versions and is used by all other packages in dev-utils.

---

## New: `setupkit-registry.yaml` (repo root)

Single source of truth for installable packages. `setupkit init` reads
this file to derive all config values automatically. `setup.sh` loops
over it to initialise plugin configs on new machines.

```yaml
repo: https://github.com/carolynboyle/dev-utils
branch: main
manifest: .doc-gen/manifest.fletch

packages:
  dbkit:
    path: python/dbkit
  fletcher:
    path: python/fletcher
  menukit:
    path: python/menukit
  setupkit:
    path: python/setupkit
  treekit:
    path: python/treekit
  viewkit:
    path: python/viewkit
```

Adding a new package to the ecosystem now requires only one new entry
in this file.

---

## Updated: `setup.sh` (repo root)

### Changes

**Added `--venv-path` argument:**

```bash
bash setup.sh                          # default: /opt/venvs/tools
bash setup.sh --venv-path /my/venv     # custom venv path
```

Non-default venv path is written to `~/.config/dev-utils/config.yaml`
under the `setupkit:` section so it persists for all subsequent
setupkit calls.

**Registry-driven plugin init loop** (Step 7, new):

Fetches `setupkit-registry.yaml` from upstream and runs
`setupkit init <name>` for each package not already configured.
Replaces the hardcoded package list from the previous version.

**Why:** New machines now get all plugin configs initialised
automatically during bootstrap, with no manual `setupkit init` calls
required.
