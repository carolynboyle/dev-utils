# tmux-launch.sh

**Path:** bash/connection tools/tmux-launch.sh
**Syntax:** bash
**Generated:** 2026-04-13 13:55:31

```bash
#!/usr/bin/env bash
# tmux-launch.sh
# Works in bash and zsh

SESSION="${1:-dev}"
shift

if [ -z "$1" ]; then
  echo "Usage: $0 session_name \"cmd1\" \"cmd2\" ..."
  exit 1
fi

# Create session if it doesn't exist
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Creating tmux session: $SESSION"
  tmux new-session -d -s "$SESSION"

  pane=0
  first=1

  for cmd in "$@"; do
    if [ "$first" -eq 1 ]; then
      tmux send-keys -t "$SESSION:0.$pane" "$cmd" C-m
      first=0
    else
      tmux split-window -h -t "$SESSION:0"
      tmux select-layout -t "$SESSION:0" tiled
      pane=$((pane + 1))
      tmux send-keys -t "$SESSION:0.$pane" "$cmd" C-m
    fi
  done
else
  echo "Session exists: $SESSION"
fi

tmux attach -t "$SESSION"
```
