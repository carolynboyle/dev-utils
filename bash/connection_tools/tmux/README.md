# tmux-launch.sh

## Description
This script automates the creation and management of tmux sessions with multiple panes, each running a specified command. It is useful for launching a set of related commands in a single tmux session, saving time and reducing manual setup.

## Features
- Creates a new tmux session with a custom name (default: `dev`).
- Splits the session into multiple panes, each running a user-specified command.
- Attaches to the session after creation.

## Usage
```bash
./tmux-launch.sh [session_name] "command1" "command2" ...
```
- `session_name`: (Optional) Name for the tmux session. Defaults to `dev`.
- `"command1"`, `"command2"`, ...: Commands to run in each pane.

### Example
```bash
./tmux-launch.sh mysession "htop" "tail -f /var/log/syslog" "vim myfile.txt"
```
This creates a tmux session named `mysession` with three panes running `htop`, `tail -f /var/log/syslog`, and `vim myfile.txt`.

## Requirements
- **tmux**: Must be installed and available in your `PATH`.
- **Bash or Zsh**: The script is compatible with both shells.

## Notes
- If the specified session already exists, the script will attach to it without modifying its panes or commands.
- The script uses a tiled layout for panes by default.