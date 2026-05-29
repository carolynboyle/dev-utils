"""
ptykit/context.py

PtyKitContext — the object passed to every plugin method.

Gives plugins access to session state, per-plugin storage, and the
ability to write to the terminal or send input to the wrapped program.

No plugin should import from wrapper.py directly. All interaction with
the PTY happens through the context object.

Usage:
    # In a plugin:
    def on_command(self, command: str, context: PtyKitContext) -> None:
        context.write("Hello from plugin!")
        my_state = context.state[self.name]
"""

from datetime import datetime
from typing import Callable


class PtyKitContext:
    """
    Runtime context passed to every plugin hook.

    Attributes:
        session_start: Datetime when the wrapper started.
        program:       Name of the wrapped CLI program.
        state:         Per-plugin storage dict, keyed by plugin name.
                       Each plugin gets its own isolated namespace.

    Methods:
        write(text): Write text to the terminal (visible to the user).
        send(text):  Send text to the wrapped program's stdin.
    """

    def __init__(
        self,
        program: str,
        write_fn: Callable[[str], None],
        send_fn: Callable[[str], None],
    ) -> None:
        """
        Initialise the context.

        Args:
            program:  Name of the wrapped CLI program (e.g. 'advent').
            write_fn: Callable that writes text to the terminal.
                      Supplied by PTYWrapper at startup.
            send_fn:  Callable that sends text to the program's stdin.
                      Supplied by PTYWrapper at startup.
        """
        self.session_start: datetime = datetime.now()
        self.program: str = program
        self.state: dict = {}
        self._write_fn = write_fn
        self._send_fn = send_fn

    def write(self, text: str) -> None:
        """
        Write text to the terminal.

        Used by plugins to display output (e.g. the map) to the user.
        Does not send anything to the wrapped program.

        Args:
            text: Text to display. Newline not added automatically.
        """
        self._write_fn(text)

    def send(self, text: str) -> None:
        """
        Send text to the wrapped program's stdin.

        Used by plugins that need to inject input into the program
        (e.g. smol-cave sending a command on behalf of the LLM).

        Args:
            text: Text to send. Include newline if the program expects it.
        """
        self._send_fn(text)
