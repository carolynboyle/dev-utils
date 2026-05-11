# setupkit_README.md

**Path:** python/setupkit/docs/designdocs/setupkit_README.md
**Syntax:** markdown
**Generated:** 2026-05-11 15:11:09

```markdown
# dev-utils Provisioning Script — Design Summary

**Status:** Design complete, not yet implemented.
**Related conversations:**
- https://claude.ai/chat/fafed263-0e83-407c-83bb-443f28a141df (devshare/shared venv session)
- https://claude.ai/chat/01000000-0000-0000-0000-000000000000 (this session)

---

## Purpose

Automate setup of the dev-utils toolkit on a fresh machine — Linux, Mac, or
Windows — with minimal prerequisites and minimal friction. No repo clone
required. A single curl command starts everything.

---

## Entry Points

### Linux / Mac

```bash
curl -fsSL https://raw.githubusercontent.com/carolynboyle/dev-utils/main/setup.sh | bash
```

### Windows

```powershell
irm https://raw.githubusercontent.com/carolynboyle/dev-utils/main/setup.ps1 | iex
```

Both entry point scripts are thin launchers. They verify Python is available,
pull down `setup/provision.py`, and hand off. All real logic lives in Python.

---

## File Structure

```
dev-utils/
├── setup.sh                  ← Linux/Mac entry point (thin launcher)
├── setup.ps1                 ← Windows entry point (thin launcher)
└── setup/
    ├── provision.py          ← main provisioning logic (cross-platform)
    ├── plugins.yaml          ← available plugins config (drives the menu)
    ├── lib.sh                ← shared bash helpers
    ├── check_deps.sh         ← system dep checks (bash)
    └── check_deps.ps1        ← system dep checks (PowerShell)
```

---

## Plugin Registry

`setup/plugins.yaml` is the single source of truth for what's available.
Only production-ready plugins are listed. Adding a new plugin when it's ready
is a yaml edit — it appears in the install menu automatically. Incomplete
tools (e.g. mcpkit) are simply absent from the file.

```yaml
plugins:
  menukit:
    description: YAML-driven CLI menu library
    readme: https://github.com/carolynboyle/dev-utils/blob/main/python/menukit/README.md
    test: import

  dbkit:
    description: Database abstraction layer (PostgreSQL + SQLite)
    readme: https://github.com/carolynboyle/dev-utils/blob/main/python/dbkit/README.md
    test: import

  fletcher:
    description: Raw GitHub URL generator
    readme: https://github.com/carolynboyle/dev-utils/blob/main/python/fletcher/README.md
    test: import

  setupkit:
    description: Plugin lifecycle manager
    readme: https://github.com/carolynboyle/dev-utils/blob/main/python/setupkit/README.md
    test: import

  todo:
    description: JSON-backed todo list manager
    readme: https://github.com/carolynboyle/dev-utils/blob/main/python/todo/README.md
    test: import

  viewkit:
    description: YAML-driven SQL view and query builder
    readme: https://github.com/carolynboyle/dev-utils/blob/main/python/viewkit/README.md
    test: import

  contactkit:
    description: Multi-format contact import and CLI interface
    readme: https://github.com/carolynboyle/dev-utils/blob/main/python/contactkit/README.md
    test: import
```

---

## Provisioning Flow

```
1. Check system dependencies
       python3 present? pip present? curl/unzip present?
       Warn on missing — do not auto-install OS-level deps.

2. Create tools venv (if not already present)
       Linux/Mac: /opt/venvs/tools
       Windows:   %APPDATA%\dev-utils\venvs\tools

3. Install setupkit into the tools venv
       Via pip from GitHub — no repo clone required.

4. Present plugin selection menu
       Reads setup/plugins.yaml.
       For each plugin: show name, description, prompt y/N.
       User selects which plugins to install.

5. Run setupkit init for each selected plugin
       Interactive — prompts for manifest URL, path prefix, etc.
       Writes ~/.config/dev-utils/setupkit/<name>.yaml.

6. Run setupkit install for each initialized plugin
       Installs selected plugins into the tools venv.

7. Verify each installed plugin
       test: import — attempts to import the package.
       Records pass/fail per plugin.

8. Generate INSTALLED.md
       Written to platform data directory.
       Contains: installed tools, skipped tools, links to READMEs.

9. Print summary to terminal
       Brief: what installed, what skipped, any failures.
       Print path to INSTALLED.md.
       Prompt: "Open it? [y/N]"
       If y: open with xdg-open (Linux), open (Mac), os.startfile (Windows).
```

---

## Verification

"Package works" means "imports cleanly." The provisioner does not test live
database connections or network services — those are configuration concerns,
not installation concerns. A tool like dbkit can be installed and importable
even if its backing database (steward) is not yet reachable. Connection
configuration is handled separately after install.

```yaml
test: import   # attempts: import <package_name>
```

Additional test types may be added to the yaml spec in future without
changing the provisioner logic.

---

## Generated Output: INSTALLED.md

Written to the platform data directory at the end of a successful provision
run.

**Linux/Mac:** `~/.local/share/dev-utils/INSTALLED.md`
**Windows:** `%APPDATA%\dev-utils\INSTALLED.md`

Content:
- Timestamp and platform
- List of installed tools with brief description
- List of available but skipped tools
- GitHub README links for all tools
- Next steps section (e.g. "dbkit requires PostgreSQL credentials — see the
  dbkit README for configuration instructions")

---

## Platform Data Directory

Determined at runtime in `config.py` — never hardcoded:

```python
import platform
from pathlib import Path

if platform.system() == "Windows":
    base = Path.home() / "AppData" / "Roaming" / "dev-utils"
else:
    base = Path.home() / ".local" / "share" / "dev-utils"
```

---

## Also Exposed As

```bash
setupkit provision
```

A thin subcommand wrapper that calls `setup/provision.py` directly. Useful
for re-provisioning or provisioning additional plugins after initial setup
without re-running the curl bootstrap.

---

## Open Questions (resolved)

| Question | Decision |
|---|---|
| Where does it live? | `setup/provision.py`, also `setupkit provision` subcommand |
| How do plugin configs get onto a fresh machine? | Interactive `setupkit init` during provision run |
| What does "package works" mean? | Imports cleanly; no live service testing |
| Terminal output or report file? | Both — terminal summary + generated `INSTALLED.md` |

---

## Not In Scope

- Installing OS-level dependencies (git, python3, curl) — provisioner warns
  if missing, does not install them
- Testing live database or network service connections
- Windows path translation for editable installs (tracked separately)

```
