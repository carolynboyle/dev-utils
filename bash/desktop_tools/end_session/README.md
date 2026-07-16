# end_session

A bash script for cleanly terminating an xrdp session on an LMDE (or other
Debian-based) VM, so that the next connection gets a fresh login rather than
resuming a stale session.

## Why this exists

xrdp-sesman is designed to preserve sessions across disconnects so you can
resume where you left off. This is useful in some contexts but a liability when
a VM is misbehaving — simply closing the Windows App RDP window leaves the
session running on the VM, and reconnecting drops you straight back into it,
misbehavior and all.

`end_session` works around this by:

1. Sending polite close requests to all open windows simultaneously and waiting
   for them to respond (giving time to answer save/cancel prompts)
2. Force-killing any windows that didn't close on their own
3. Cleaning up Chrome singleton lock files that cause Chrome to refuse to start
   after an unclean shutdown
4. Calling `loginctl terminate-session` to tear down the session cgroup
   completely, so xrdp-sesman has nothing to resume on the next connection

For this to work, `xrdp-sesman` must be configured with `KillDisconnected=true`
in `/etc/xrdp/sesman.ini`. Without this, sesman will preserve the session
regardless of what the script does.

## Dependencies

- `wmctrl`
- `xdotool`

Install with:

```
| Distribution | `wmctrl` Package Name | `xdotool` Package Name | Install Command |
| :--- | :--- | :--- | :--- |
| **Debian** (and Ubuntu/Mint) | `wmctrl` | `xdotool` | `sudo apt install wmctrl xdotool` |
| **Arch Linux** | `wmctrl` | `xdotool` | `sudo pacman -S wmctrl xdotool` |
| **RHEL** (and Rocky/AlmaLinux) | `wmctrl` | `xdotool` | `sudo dnf install wmctrl xdotool` |
```

## Usage

Run from a desktop shortcut. The default wait time is 10 seconds — long enough
to respond to save/cancel prompts before pass 2 force-closes anything still
open.

To adjust the wait time, edit the `Exec` line of the desktop shortcut and add
the number of seconds at the end:

```
Exec=end_session 5
```

## Log file

Each run overwrites `~/.local/share/end_session.log`.
