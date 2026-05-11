# provisioning_design.md

**Path:** python/setupkit/docs/designdocs/provisioning_design.md
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

2. Prompt for venv install scope
       Linux/Mac:
         [1] All users  — /opt/venvs/tools (requires sudo; chown'd to $USER)
         [2] This user  — ~/.local/venvs/tools
         [3] Custom path
       Windows (run as Administrator for option 1):
         [1] All users  — C:\tools\venvs\tools (requires admin elevation)
         [2] This user  — %LOCALAPPDATA%\dev-utils\venvs\tools
         [3] Custom path
       Chosen path written to ~/.config/dev-utils/config.yaml as venv_path.
       On Linux/Mac, /opt is created with sudo then chown'd to $USER —
       no further sudo required.

3. Create tools venv at chosen path (if not already present)

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

## Prerequisites and Error Handling

The entry point scripts (`setup.sh` / `setup.ps1`) run before Python is
available, so they are responsible for catching any can't-proceed conditions
and printing clear, actionable messages. The provisioner never tries to
install OS-level dependencies — it explains what's missing and exits cleanly.

### Python not found or wrong version

```
dev-utils requires Python 3.11 or later.
Python was not found on your system (or the version found is too old).

Install or upgrade it from: https://www.python.org/downloads/

  Linux:    sudo apt install python3.11
  Mac:      brew install python3
  Windows:  winget install Python.Python.3.11

Then re-run this script.
```

Exit with non-zero exit code. Do not proceed.

### pip not found

```
pip was not found. It is required to install dev-utils packages.

  Linux:    sudo apt install python3-pip
  Mac:      python3 -m ensurepip --upgrade
  Windows:  python -m ensurepip --upgrade

Then re-run this script.
```

Exit with non-zero exit code. Do not proceed.

### curl not found (Linux/Mac only)

```
curl was not found. It is required to download dev-utils packages.

  Linux:    sudo apt install curl
  Mac:      brew install curl

Then re-run this script.
```

Exit with non-zero exit code. Do not proceed.

### venv module not found

```
The Python venv module was not found.

  Linux:    sudo apt install python3-venv
  Mac/Win:  included with standard Python — try reinstalling Python 3.11+

Then re-run this script.
```

Exit with non-zero exit code. Do not proceed.

### All-users install without elevation

**Linux/Mac:** sudo prompt fails or is declined.
```
Could not create /opt/venvs/tools — sudo access is required for an
all-users install. Re-run as root, or choose a single-user install path.
```

**Windows:** provisioner detects it is not running as Administrator.
```
An all-users install requires Administrator privileges.
Please close this window, right-click Command Prompt or PowerShell,
select "Run as Administrator", and re-run the script.
```

Exit with non-zero exit code in both cases. Do not proceed.

### Plugin install failure

A failure installing one plugin does not abort the run. The provisioner
logs the failure, records it in the terminal summary and INSTALLED.md, and
continues to the next plugin. The user is informed at the end:

```
fletcher        installed   ✓
dbkit           installed   ✓
menukit         FAILED      ✗  see ~/.local/share/dev-utils/provision.log
```

### Network unavailable

If the provisioner cannot reach GitHub to fetch a plugin:
```
Could not reach GitHub to install <plugin>.
Check your network connection and re-run: setupkit install <plugin>
```

Treated as a plugin-level failure — logged, reported, provisioner continues.

---

## Windows Administrator Note

For an all-users install on Windows, open Command Prompt or PowerShell as
Administrator before running the install script. This gives the provisioner
the elevation it needs in one UAC prompt. For a single-user install, run
normally — no elevation required.

The provisioner checks whether it has admin rights when it starts. If the
user chose "all users" without elevation, it prints a clear message and
exits cleanly rather than failing partway through.

---

## What This Does To Your Computer

Nothing happens without your confirmation. The provisioner will tell you
exactly what it intends to do and prompt before making changes. The complete
list of locations it may create or modify:

**All platforms:**
- `~/.config/dev-utils/` — configuration files
- `~/.config/dev-utils/setupkit/<plugin>.yaml` — one file per installed plugin
- `~/.config/dev-utils/config.yaml` — user config (venv path and overrides)
- `~/.local/share/dev-utils/provision.log` — install log
- `~/.local/share/dev-utils/INSTALLED.md` — generated summary (Linux/Mac)
- `%APPDATA%\dev-utils\INSTALLED.md` — generated summary (Windows)
- The tools venv at your chosen path (see venv install scope above)

**Linux/Mac (all-users install only):**
- `/opt/venvs/tools/` — created with sudo, then chown'd to $USER
- `/usr/local/bin/<toolname>` — symlinks for each installed tool (requires sudo)

**Linux/Mac (single-user install only):**
- `~/.local/venvs/tools/` — tools venv
- `~/.local/bin/<toolname>` — symlinks for each installed tool

**Windows (all-users install, requires Administrator):**
- `C:\tools\venvs\tools\` — tools venv
- Entries added to system PATH

**Windows (single-user install):**
- `%LOCALAPPDATA%\dev-utils\venvs\tools\` — tools venv
- Entries added to user PATH

Nothing is written outside these locations. The provisioner does not modify
system Python, system packages, or any existing configuration files it did
not create.

---

## Install Counter

The provisioner will eventually report installs to the GitHub API as part of
the GitHub Developer Program integration. A placeholder function
`report_install()` is included in `provision.py` with a "coming soon"
docstring marking the integration point. It is a no-op until implemented.

This will record: timestamp, platform, and which plugins were installed.
No personally identifiable information is collected.

---

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
