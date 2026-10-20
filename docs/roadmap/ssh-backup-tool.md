# ssh-backup: SSH Key Backup and Distribution Tool

**Status:** Planned  
**Category:** bash/connection_tools  
**Date:** 2026-10-19

## Problem

macOS silently destroys SSH keys and config files — via iCloud Optimize Storage, OS
reinstalls, Migration Assistant gaps, or other "helpful" interventions. Recovery without
a backup requires Hetzner KVM console access, which is a miserable experience (no paste,
character mangling, terminal barely usable). This happened in October 2026 and took over
an hour to resolve.

## Goal

A single script that creates an encrypted archive of all SSH keys and config, stores it
locally in `~/projects/archives/`, and copies it to one or more remote hosts over
Tailscale. Recovery becomes: decrypt archive, extract, done.

---

## Scope

### What gets backed up

- `~/.ssh/keys/` — all private and public key files
- `~/.ssh/config` — host aliases and identity mappings
- Exclude: `~/.ssh/agent/` (socket files, not archivable), `known_hosts*` (regenerates automatically)

### What does NOT get backed up

- Private keys from remote hosts (each host is responsible for its own keys)
- Passphrases (stay in Proton Pass)

---

## Design

### Invocation

```bash
ssh-backup [--restore] [--host <tailscale-host>] [--archive-dir <path>]
```

Default behavior (no flags): backup mode, destination `hetzner-meet`, archive in
`~/projects/archives/`.

### Backup flow

1. Check that `~/.ssh/keys/` exists and is non-empty — exit early with a clear message if not
2. Build tar archive, excluding sockets and known_hosts, to a temp file
3. Check tar exit code before proceeding — don't attempt encryption of a failed archive
4. Prompt for encryption passphrase (with confirmation), using `openssl enc -aes-256-cbc -pbkdf2`
5. Write `.enc` file to `~/projects/archives/ssh_keys_backup_YYYYMMDD.enc`
   - Timestamped filename — keeps multiple versions, never silently overwrites
6. `scp` the `.enc` file to each configured remote host via Tailscale
7. Verify remote file size matches local — print confirmation
8. Clean up temp tar file
9. Print summary: local path, remote path(s), sizes, date

### Restore flow (`--restore`)

1. List available `.enc` files in archive dir, prompt user to choose one
2. Prompt for passphrase
3. Decrypt to temp tar
4. Dry-run extract first (show what will be written), ask for confirmation
5. Extract to `~/` with `--keep-old-files` to avoid clobbering newer keys
6. Print list of restored files

### Configuration

Destination hosts and archive directory read from `~/.config/ssh-backup/config.yml`
(created with sensible defaults on first run if absent):

```yaml
archive_dir: ~/projects/archives
remote_hosts:
  - hetzner-meet
remote_path: ~/archives
```

---

## Implementation notes

- Pure bash — no Python dependency, runs anywhere with OpenSSL and standard utils
- Must handle macOS `tar` (BSD) and Linux `tar` (GNU) — flag differences exist
- The `~` expansion issue in Hetzner KVM console is what motivated the Taildrop/scp
  approach — this script runs from a working shell so that's not a concern here
- OpenSSL passphrase prompt must get its own clean TTY — pipe/background context will
  break it; script should detect and warn if not running interactively
- On macOS, test that `~/.ssh/agent/` socket exclusion works with `--exclude` flag
  (BSD tar uses `--exclude=PATTERN`, same as GNU in this case)

---

## File location in dev-utils

```
bash/
  connection_tools/
    ssh-backup.sh        ← main script
    ssh-backup.yml       ← default config template
```

---

## Future

- `--hosts all` to push to every Tailscale node in `~/.ssh/config`
- Proton Drive as an additional destination (if CLI access becomes available)
- Checksum verification file alongside `.enc` archives
- Integration with a broader `wcyj-backup` strategy for other config files
  (`.ssh/config`, dotfiles, etc.)
