# dev-utils changelog — 2026-05-11

## Root-level changes

### New: `setupkit-registry.yaml`

Added to repo root. Single source of truth for all installable packages
in dev-utils. Replaces hardcoded package lists in `setup.sh` and manual
URL entry in `setupkit init`. See setupkit changedoc for full details.

### Updated: `setup.sh`

- Added `--venv-path` argument for non-default venv locations
- Writes venv path override to `~/.config/dev-utils/config.yaml` for persistence
- Registry-driven plugin init loop replaces hardcoded package list
- Idempotent — skips plugins that already have a config

### New package: `python/treekit/`

treekit 0.1.0 — creates directory trees from markdown structure
specifications. CLI and importable library. Full test suite (134 tests).
See `python/treekit/README.md` for usage.

---

## Detailed changedocs

Full BEFORE/AFTER changedoc for setupkit modifications:
`python/setupkit/docs/changedocs/changelog-2026-05-11.md`
