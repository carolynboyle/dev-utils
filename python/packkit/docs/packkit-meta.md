# pack-kit: .gitignore and README.md

---

## .gitignore

```
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
*.egg
*.egg-info/
dist/
build/
eggs/
parts/
var/
sdist/
wheels/
pip-wheel-metadata/
share/python-wheels/
.installed.cfg
lib/
lib64/
MANIFEST

# Virtual environments
.venv/
venv/
ENV/
env/
.env

# pytest
.pytest_cache/
.cache/
htmlcov/
.coverage
.coverage.*
coverage.xml
*.cover

# Distribution / packaging
*.tar.gz
*.whl

# Pack run output — tarballs are never committed
# Your packkit.yaml configs are host-specific and may contain paths
# Keep them out of the repo
packkit.yaml
*.packkit.yaml

# Logs
*.log

# Editors
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
```

---

## README.md

```markdown
# pack-kit

Server configuration archive tool for the dev-utils toolkit.

Reads a `packkit.yaml` config file, collects specified files, directories,
and command output into a timestamped tarball, and optionally ships it to
a remote host via scp. Designed for backing up server configuration before
a wipe, migration, or major upgrade.

---

## Installation

### Via setupkit (recommended)

```bash
setupkit install packkit
```

### From dev-utils repo (development mode)

```bash
cd ~/projects/dev-utils/python/packkit
pip install -e .
```

Verify:

```bash
packkit --help
```

---

## Quick Start

Create a `packkit.yaml` in your working directory (copy from
`data/packkit.yaml.template` and edit):

```yaml
pack_name: my-server
destination: /tmp

files:
  - /etc/ssh/sshd_config
  - /etc/hostname

commands:
  - label: os-release
    run: cat /etc/os-release
  - label: installed-packages
    run: rpm -qa

ship:
  enabled: false
```

Preview what will be collected:

```bash
packkit --dry-run
```

Run the pack:

```bash
packkit
```

Use a named config file:

```bash
packkit --config /path/to/my-server.yaml
```

---

## Config File

pack-kit looks for `packkit.yaml` in the current directory by default.
Use `--config` to specify a different path. Keeping one config per host
(e.g. `wcyj-meet.yaml`, `yoga.yaml`) and running from a configs directory
is the recommended pattern.

### Full config reference

```yaml
pack_name: my-server          # Used as the tarball base name (required)
destination: /tmp             # Where the tarball is created locally
                              # Defaults to /tmp if omitted

files:                        # Individual files to collect
  - /etc/ssh/sshd_config
  - /etc/hostname
  - /etc/hosts

directories:                  # Directories to collect recursively
  - /etc/myapp
  - /etc/docker

commands:                     # Commands to run; output saved as commands/<label>.txt
  - label: os-release
    run: cat /etc/os-release
  - label: installed-packages
    run: rpm -qa              # RHEL/AlmaLinux/Rocky
  # run: dpkg -l              # Debian/Ubuntu
  - label: running-services
    run: systemctl list-units --type=service --state=running

ship:
  enabled: false              # Set true to scp the tarball to a remote host
  user: carolyn
  host: 192.168.10.2
  path: /srv/exports/storage/backups
  key: ~/.ssh/id_ed25519      # Omit to use ssh agent
```

---

## Archive Structure

The tarball is named `<pack_name>-<timestamp>.tar.gz` and contains:

```
my-server-20260609-143022/
├── etc/
│   ├── ssh/
│   │   └── sshd_config
│   ├── hostname
│   └── hosts
└── commands/
    ├── os-release.txt
    ├── installed-packages.txt
    └── running-services.txt
```

Files and directories preserve their original absolute path structure.
Command output is collected as flat text files under `commands/`.

---

## Failure Behaviour

Any failure — missing file, failed command, scp error — aborts the run
immediately. No partial archives are created. The run log is printed to
stdout and written to disk, so you always know exactly what happened.

---

## Logging

Every run appends a plain-text entry to:

```
~/.config/dev-utils/packkit/packkit.log
```

The log is also printed to stdout on completion (success or failure) and
serves as the run report.

Example entry:

```
=== 2026-06-09 14:30:22 ===
Pack:   wcyj-meet
Status: SUCCESS

Starting pack run: wcyj-meet-20260609-143022
Collecting file: /etc/ssh/sshd_config
Collecting file: /etc/hostname
Collecting directory: /etc/headscale
Running command: os-release
Running command: installed-packages
Shipping to carolyn@192.168.10.2:/srv/exports/storage/backups
Transfer complete.
Archive created: /tmp/wcyj-meet-20260609-143022.tar.gz
===
```

---

## Options

| Option | Short | Description |
|---|---|---|
| `--config FILE` | `-c` | Path to config file. Defaults to `packkit.yaml` in cwd. |
| `--dry-run` | `-n` | Print what would be collected without creating an archive. |

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success, or dry run completed. |
| `1` | Collection, pack, or ship error. |
| `2` | Config not found or invalid. |

---

## As a Library

```python
from pathlib import Path
from packkit import load_config, Packer, RunLogger

config = load_config('/path/to/packkit.yaml')
logger = RunLogger(config.pack_name)
packer = Packer(config, logger)
tarball = packer.run()
logger.close(success=True)
```

---

## Host-Specific Configs

Keep one config file per host. These are never committed to the repo
(see `.gitignore`) since they contain host-specific paths and may
reference key files.

Recommended location: `~/.config/dev-utils/packkit/<hostname>.yaml`

---

## Dependencies

- Python 3.11+
- `pyyaml>=6.0`

---

## Development

### Install in dev mode

```bash
cd ~/projects/dev-utils/python/packkit
pip install -e .
```

### Run tests

```bash
pytest tests/
```

### Lint

```bash
pylint src/packkit
```

---

## License

MIT License. See `LICENSE` file in this directory.

---

## Part of Project Crew

pack-kit is one tool in the Project Crew / dev-utils ecosystem:

- **doc-gen** — filesystem manifest generator
- **fletcher** — GitHub URL manifest generator
- **treekit** — directory tree scaffolding from markdown
- **setupkit** — plugin lifecycle manager
- **menukit** — YAML-driven menu library
- **dbkit** — PostgreSQL/SQLite abstraction layer
- **viewkit** — YAML-driven SQL query and view builder
- **contactkit** — multi-format contact import
- **todo** — task manager with JSON storage
- **pack-kit** — server configuration archive and transfer

---

## Author

Carolyn Boyle
```
