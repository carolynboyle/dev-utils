"""
ptykit/wrapper.py

PTYWrapper — spawns a CLI program in a pseudo-terminal, streams stdout
to the terminal, intercepts configured commands before they reach the
program, and dispatches to registered plugins.

This is the core of ptykit. Everything else supports this module.

Usage:
    from ptykit.config import ConfigLoader
    from ptykit.context import PtyKitContext
    from ptykit.plugin import PluginRegistry
    from ptykit.wrapper import PTYWrapper

    config = ConfigLoader("advent")
    registry = PluginRegistry(config.plugins)
    wrapper = PTYWrapper(config, registry)
    wrapper.run()
"""

import logging
import os
import select
import sys
import tty
import termios

import ptyprocess

from ptykit.config import ConfigLoader
from ptykit.context import PtyKitContext
from ptykit.exceptions import PtyKitWrapperError
from ptykit.plugin import PluginRegistry

log = logging.getLogger("ptykit")

# Read buffer size for PTY output
_BUFSIZE = 1024


class PTYWrapper:
    """
    Spawns a CLI program in a PTY and wraps it with plugin support.

    stdout from the program is streamed to the terminal line by line.
    Each line is passed to all registered plugins via on_output().

    stdin from the user is buffered until newline. If the input matches
    an intercept command, on_command() is called on all plugins and the
    input is NOT passed to the program. Otherwise input passes through
    unchanged.

    Usage:
        wrapper = PTYWrapper(config, registry)
        wrapper.run()
    """

    def __init__(self, config: ConfigLoader, registry: PluginRegistry) -> None:
        """
        Initialise the wrapper.

        Args:
            config:   Loaded ConfigLoader instance.
            registry: Loaded PluginRegistry instance.
        """
        self._config = config
        self._registry = registry
        self._process: ptyprocess.PtyProcess | None = None
        self._context: PtyKitContext | None = None

    def run(self) -> None:
        """
        Start the wrapped program and enter the IO loop.

        Spawns the program in a PTY, calls on_start() on all plugins,
        then loops reading stdout and stdin until the program exits.
        Calls on_exit() on all plugins before returning.

        Raises:
            PtyKitWrapperError: If the program cannot be spawned.
        """
        self._spawn()
        self._context = PtyKitContext(
            program=self._config.program,
            write_fn=self._write,
            send_fn=self._send,
        )
        self._registry.on_start(self._context)

        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            self._loop()
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            self._registry.on_exit(self._context)

    def _spawn(self) -> None:
        """
        Spawn the configured program in a PTY.

        Raises:
            PtyKitWrapperError: If the program cannot be found or started.
        """
        program = self._config.program
        log.debug("Spawning: %s", program)
        try:
            self._process = ptyprocess.PtyProcess.spawn([program])
        except FileNotFoundError as exc:
            raise PtyKitWrapperError(
                f"Program not found: {program!r}. "
                f"Is it installed and on PATH?"
            ) from exc
        except Exception as exc:
            raise PtyKitWrapperError(
                f"Failed to spawn {program!r}: {exc}"
            ) from exc

    def _loop(self) -> None:
        """
        Main IO loop. Reads stdout and stdin until the program exits.

        stdout lines are passed to plugins via on_output().
        stdin is buffered; intercepted commands go to on_command(),
        everything else passes through to the program.
        """
        input_buffer = ""

        while self._process.isalive():
            try:
                fds = select.select(
                    [self._process.fd, sys.stdin.fileno()], [], [], 0.05
                )[0]
            except (ValueError, OSError):
                break

            # -- Program stdout ----------------------------------------------
            if self._process.fd in fds:
                try:
                    data = os.read(self._process.fd, _BUFSIZE)
                except OSError:
                    break

                text = data.decode("utf-8", errors="replace")
                sys.stdout.write(text)
                sys.stdout.flush()

                for line in text.splitlines():
                    self._registry.on_output(line.strip(), self._context)

            # -- User stdin --------------------------------------------------
            if sys.stdin.fileno() in fds:
                try:
                    char = sys.stdin.read(1)
                except OSError:
                    break

                if char in ("\r", "\n"):
                    command = input_buffer.strip().lower()
                    input_buffer = ""

                    if command in self._config.intercept:
                        log.debug("Intercepted command: %r", command)
                        self._registry.on_command(command, self._context)
                    else:
                        self._send(command + "\n")
                else:
                    input_buffer += char
                    sys.stdout.write(char)
                    sys.stdout.flush()

    def _write(self, text: str) -> None:
        """
        Write text to the terminal (stdout).

        Args:
            text: Text to display. Newline not added automatically.
        """
        sys.stdout.write(text)
        sys.stdout.flush()

    def _send(self, text: str) -> None:
        """
        Send text to the wrapped program's stdin via the PTY.

        Args:
            text: Text to send to the program.
        """
        if self._process and self._process.isalive():
            self._process.write(text.encode("utf-8"))
