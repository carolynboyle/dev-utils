# cli.py

**Path:** python/treekit/src/treekit/cli.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
cli.py — Command-line entry point for treekit.

Reads a markdown tree specification from a file or stdin, parses it into
a Node tree, and creates the corresponding directory and file structure
on disk.

Usage:
    treekit structure.md
    treekit structure.md --output ~/projects
    treekit structure.md --dry-run
    cat structure.md | treekit
    cat structure.md | treekit --output ~/projects --dry-run
"""

import argparse
import sys
from pathlib import Path

from treekit.builder import TreeBuilder
from treekit.exceptions import (
    BuildError,
    EmptyInputError,
    LogError,
    NoTreeFoundError,
    OutputPathError,
    ParseError,
    TkPermissionError,
    TreekitError,
)
from treekit.parser import TreeParser


_EXIT_OK = 0
_EXIT_ERROR = 1
_EXIT_BAD_ARGS = 2


def main() -> None:
    """Entry point — parse arguments, run treekit, handle all exceptions."""
    args = _parse_args()
    text, source_label = _read_input(args.source)

    if text is None:
        sys.exit(_EXIT_ERROR)

    # --- Parse ---------------------------------------------------------------
    parser = TreeParser()
    try:
        root = parser.parse(text)
    except EmptyInputError as exc:
        _error(f"Empty input: {exc}")
        sys.exit(_EXIT_ERROR)
    except NoTreeFoundError as exc:
        _error(f"No tree structure found: {exc}")
        sys.exit(_EXIT_ERROR)
    except ParseError as exc:
        _error(f"Parse error: {exc}")
        sys.exit(_EXIT_ERROR)

    output_path = Path(args.output).expanduser().resolve()

    # --- Dry run -------------------------------------------------------------
    if args.dry_run:
        dry_builder = TreeBuilder(
            output_path=output_path,
            dry_run=True,
            source=source_label,
        )
        try:
            dry_result = dry_builder.build(root)
        except OutputPathError as exc:
            _error(f"Output path error: {exc}")
            sys.exit(_EXIT_ERROR)
        except (BuildError, TreekitError) as exc:
            _error(f"Build error: {exc}")
            sys.exit(_EXIT_ERROR)

        _print_dry_run(dry_result.created, output_path)

        root_name = dry_result.created[0].rstrip('/') if dry_result.created else ''
        target_display = output_path / root_name
        if not _confirm(f"Create this structure in {target_display}? [y/N] "):
            print("Aborted.")
            sys.exit(_EXIT_OK)

    # --- Live build ----------------------------------------------------------
    builder = TreeBuilder(
        output_path=output_path,
        dry_run=False,
        source=source_label,
    )

    log_error: LogError | None = None

    try:
        result = builder.build(root)
    except OutputPathError as exc:
        _error(f"Output path error: {exc}")
        sys.exit(_EXIT_ERROR)
    except TkPermissionError as exc:
        _error(f"Permission denied: {exc}")
        sys.exit(_EXIT_ERROR)
    except LogError as exc:
        # Build succeeded but log failed — capture and report after summary.
        log_error = exc
        result = None
    except (BuildError, TreekitError) as exc:
        _error(f"Build error: {exc}")
        sys.exit(_EXIT_ERROR)

    if result is not None:
        _print_summary(result)

    if log_error is not None:
        _warn(f"Log write failed (build succeeded): {log_error}")

    sys.exit(_EXIT_OK)


# -----------------------------------------------------------------------------
# Private helpers
# -----------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    """
    Build and return the parsed argument namespace.

    Returns:
        Parsed argparse.Namespace.
    """
    parser = argparse.ArgumentParser(
        prog='treekit',
        description='Create a directory tree from a markdown structure specification.',
    )
    parser.add_argument(
        'source',
        nargs='?',
        default=None,
        metavar='FILE',
        help='Markdown file containing the tree specification. Reads from stdin if omitted.',
    )
    parser.add_argument(
        '--output', '-o',
        default='.',
        metavar='DIR',
        help='Directory under which the tree will be created. Defaults to current directory.',
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Print what would be created and prompt for confirmation before acting.',
    )
    return parser.parse_args()


def _read_input(source: str | None) -> tuple[str | None, str]:
    """
    Read the markdown input from a file or stdin.

    Args:
        source: File path string, or None to read from stdin.

    Returns:
        Tuple of (text content or None on error, source label for logging).
    """
    if source is None:
        if sys.stdin.isatty():
            _error("No input file specified and stdin is a terminal. Provide a FILE or pipe input.")
            return None, 'stdin'
        try:
            return sys.stdin.read(), 'stdin'
        except OSError as exc:
            _error(f"Failed to read from stdin: {exc}")
            return None, 'stdin'

    path = Path(source).expanduser()
    if not path.exists():
        _error(f"File not found: {path}")
        return None, str(path)
    if not path.is_file():
        _error(f"Not a file: {path}")
        return None, str(path)

    try:
        return path.read_text(encoding='utf-8'), str(path)
    except OSError as exc:
        _error(f"Could not read file {path}: {exc}")
        return None, str(path)


def _print_dry_run(created: list[str], output_path: Path) -> None:
    """
    Print the dry-run tree to stdout.

    Args:
        created:     List of paths that would be created.
        output_path: Resolved output directory.
    """
    print(f"\nDry run — output: {output_path}\n")
    print("Would create:")
    for entry in created:
        print(f"  {entry}")
    print()


def _print_summary(result) -> None:
    """
    Print the post-build summary to stdout.

    Args:
        result: Completed BuildResult.
    """
    print(f"\nOutput: {result.output}\n")

    if result.created:
        print(f"Created ({len(result.created)}):")
        for entry in result.created:
            print(f"  {entry}")

    if result.skipped:
        print(f"\nSkipped — already exists ({len(result.skipped)}):")
        for entry in result.skipped:
            print(f"  {entry}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for path, message in result.errors:
            print(f"  {path}: {message}")

    print()


def _confirm(prompt: str) -> bool:
    """
    Prompt the user for a yes/no confirmation.

    Args:
        prompt: Text to display.

    Returns:
        True if the user entered 'y' or 'Y', False otherwise.
    """
    try:
        response = input(prompt).strip().lower()
        return response == 'y'
    except (KeyboardInterrupt, EOFError):
        print()
        return False


def _error(message: str) -> None:
    """Print an error message to stderr."""
    print(f"treekit: error: {message}", file=sys.stderr)


def _warn(message: str) -> None:
    """Print a warning message to stderr."""
    print(f"treekit: warning: {message}", file=sys.stderr)


if __name__ == '__main__':
    main()

```
