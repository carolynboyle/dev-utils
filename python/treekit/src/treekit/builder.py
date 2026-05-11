"""
builder.py — Filesystem tree builder for treekit.

Consumes a Node tree produced by TreeParser and either performs a dry run
(prints what would be created) or creates the directory and file structure
on disk. Writes a plain-text run log on completion.

Typical usage:
    builder = TreeBuilder(output_path=Path('/home/carolyn/projects'), dry_run=False)
    result = builder.build(root_node)
"""

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from treekit.exceptions import BuildError, LogError, OutputPathError, PathCollisionError, TkPermissionError
from treekit.node import Node


_LOG_DIR = Path.home() / '.config' / 'dev-utils' / 'treekit'
_LOG_FILE = _LOG_DIR / 'treekit.log'


@dataclass
class BuildResult:
    """
    Outcome of a single TreeBuilder.build() call.

    Attributes:
        source:   Path or label for the input source (file path or 'stdin').
        output:   Resolved output path.
        dry_run:  True if this was a dry run.
        created:  Paths successfully created.
        skipped:  Paths that already existed and were left untouched.
        errors:   (path, message) pairs for any failures.
    """
    source: str
    output: Path
    dry_run: bool
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if no errors were recorded."""
        return len(self.errors) == 0


class TreeBuilder:
    """
    Creates a filesystem tree from a Node tree.

    In dry-run mode the tree is printed and no filesystem changes are made.
    In live mode directories and empty files are created under output_path.
    A plain-text log entry is appended to ~/.config/dev-utils/treekit/treekit.log
    after every run, dry or live.

    Args:
        output_path: Directory under which the tree will be created.
        dry_run:     If True, print intended actions without creating anything.
        source:      Label for the input source — used in log output.
    """

    def __init__(
        self,
        output_path: Path,
        dry_run: bool = False,
        source: str = 'unknown',
    ) -> None:
        self._output_path = output_path.resolve()
        self._dry_run = dry_run
        self._source = source

    def build(self, root: Node) -> BuildResult:
        """
        Execute the build from a Node tree.

        Args:
            root: Root Node as returned by TreeParser.parse().

        Returns:
            BuildResult with created, skipped, and error records.

        Raises:
            OutputPathError: If output_path does not exist or is not a directory.
            BuildError:      If the build fails for an unrecoverable reason.
        """
        if not self._output_path.exists():
            raise OutputPathError(f"Output path does not exist: {self._output_path}")
        if not self._output_path.is_dir():
            raise OutputPathError(f"Output path is not a directory: {self._output_path}")

        result = BuildResult(
            source=self._source,
            output=self._output_path,
            dry_run=self._dry_run,
        )

        self._walk(root, self._output_path, result)
        self._write_log(result)

        return result

    # -------------------------------------------------------------------------
    # Private methods
    # -------------------------------------------------------------------------

    def _walk(self, node: Node, current_path: Path, result: BuildResult) -> None:
        """
        Recursively walk the Node tree, creating paths or recording dry-run entries.

        Args:
            node:         Current Node being processed.
            current_path: Filesystem path corresponding to the current node.
            result:       BuildResult accumulator.
        """
        target = current_path / node.name
        relative = str(target.relative_to(self._output_path))

        if node.is_dir:
            can_walk = self._handle_directory(target, relative, result)
        else:
            can_walk = False
            self._handle_file(target, relative, result)

        if can_walk or not node.is_dir:
            for child in node.children:
                self._walk(child, target, result)

    def _handle_directory(self, target: Path, relative: str, result: BuildResult) -> bool:
        """
        Create a directory or record the dry-run intention.

        Args:
            target:   Absolute path to create.
            relative: Path relative to output root, for display and logging.
            result:   BuildResult accumulator.

        Returns:
            True if children should be walked, False if a collision blocked it.
        """
        label = relative + '/'

        if self._dry_run:
            result.created.append(label)
            return True

        if target.exists():
            if target.is_dir():
                result.skipped.append(label)
                return True
            result.errors.append((label, "Path exists as a file, expected directory."))
            return False

        try:
            target.mkdir(parents=True, exist_ok=True)
            result.created.append(label)
            return True
        except PermissionError as exc:
            raise TkPermissionError(f"Permission denied creating directory: {target}") from exc
        except OSError as exc:
            raise BuildError(f"Failed to create directory {target}: {exc}") from exc

    def _handle_file(self, target: Path, relative: str, result: BuildResult) -> None:
        """
        Create an empty file or record the dry-run intention.

        Args:
            target:   Absolute path to create.
            relative: Path relative to output root, for display and logging.
            result:   BuildResult accumulator.
        """
        if self._dry_run:
            result.created.append(relative)
            return

        if target.exists():
            if target.is_file():
                result.skipped.append(relative)
            else:
                result.errors.append((relative, "Path exists as a directory, expected file."))
            return

        try:
            target.touch()
            result.created.append(relative)
        except PermissionError as exc:
            raise TkPermissionError(f"Permission denied creating file: {target}") from exc
        except OSError as exc:
            raise BuildError(f"Failed to create file {target}: {exc}") from exc

    def _write_log(self, result: BuildResult) -> None:
        """
        Append a plain-text run record to the treekit log file.

        Log write failures are caught and re-raised as LogError — they do
        not abort a successful build.

        Args:
            result: Completed BuildResult to record.

        Raises:
            LogError: If the log directory cannot be created or the log
                      cannot be written.
        """
        try:
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise LogError(f"Could not create log directory {_LOG_DIR}: {exc}") from exc

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        dry_label = 'yes' if result.dry_run else 'no'

        lines: list[str] = [
            f"=== {timestamp} ===",
            f"Source:   {result.source}",
            f"Output:   {result.output}",
            f"Dry-run:  {dry_label}",
            "",
        ]

        if result.created:
            lines.append("CREATED:" if not result.dry_run else "WOULD CREATE:")
            for path in result.created:
                lines.append(f"  {path}")
            lines.append("")

        if result.skipped:
            lines.append("SKIPPED (already exists):")
            for path in result.skipped:
                lines.append(f"  {path}")
            lines.append("")

        if result.errors:
            lines.append("ERRORS:")
            for path, message in result.errors:
                lines.append(f"  {path}: {message}")
            lines.append("")

        lines.append("===\n")

        try:
            with open(_LOG_FILE, 'a', encoding='utf-8') as log:
                log.write('\n'.join(lines))
        except OSError as exc:
            raise LogError(f"Could not write to log file {_LOG_FILE}: {exc}") from exc
