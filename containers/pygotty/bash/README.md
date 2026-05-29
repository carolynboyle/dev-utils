# pygotty/bash

GoTTY serving a bash shell in a browser tab.

Connection persists until you explicitly type `exit` or Ctrl+D.
Unlike the parent pygotty container (python3), bash does not exit
on Ctrl+C — interrupt signals go to the running command, not the shell.

Part of the pygotty container family in dev-utils.