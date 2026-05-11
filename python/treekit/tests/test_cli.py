"""
test_cli.py — Tests for the treekit CLI entry point.

Covers:
    - File input happy path: tree created, exit 0
    - Stdin input happy path: tree created, exit 0
    - --dry-run flag: builder called with dry_run=True, nothing created
    - --output flag: output path passed correctly to builder
    - Missing input file: error message to stderr, exit 1
    - Empty input file: EmptyInputError handled, exit 1
    - No tree content: NoTreeFoundError handled, exit 1
    - stdin is a tty with no file argument: error message, exit 2
    - LogError: warning printed, exit 0 (build succeeded)
    - Parse error: handled cleanly, exit 1
"""

import sys
import unittest.mock
from pathlib import Path

import pytest

from treekit.cli import main
from treekit.exceptions import EmptyInputError, LogError, NoTreeFoundError


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

SIMPLE_MARKDOWN = """\
```
simple_project/
├── src/
│   └── main.py
└── README.md
```
"""


def run_main(argv: list[str], monkeypatch) -> None:
    """
    Run cli.main() with the given sys.argv.

    Args:
        argv:       Argument list, including the program name as argv[0].
        monkeypatch: pytest monkeypatch fixture for patching sys.argv.
    """
    monkeypatch.setattr(sys, 'argv', argv)
    main()


# -----------------------------------------------------------------------------
# File input
# -----------------------------------------------------------------------------

class TestFileInput:
    """CLI reads from a file argument correctly."""

    def test_file_input_exits_zero(self, tmp_path, monkeypatch, capsys):
        """Valid file input produces exit 0."""
        spec = tmp_path / 'structure.md'
        spec.write_text(SIMPLE_MARKDOWN, encoding='utf-8')

        log_dir = tmp_path / 'log'
        log_file = log_dir / 'treekit.log'

        with unittest.mock.patch('treekit.builder._LOG_DIR', log_dir), \
             unittest.mock.patch('treekit.builder._LOG_FILE', log_file), \
             pytest.raises(SystemExit) as exc_info:
            run_main(['treekit', str(spec), '--output', str(tmp_path)], monkeypatch)

        assert exc_info.value.code == 0

    def test_file_input_creates_structure(self, tmp_path, monkeypatch, capsys):
        """Valid file input creates the expected directory structure."""
        spec = tmp_path / 'structure.md'
        spec.write_text(SIMPLE_MARKDOWN, encoding='utf-8')

        log_dir = tmp_path / 'log'
        log_file = log_dir / 'treekit.log'

        with unittest.mock.patch('treekit.builder._LOG_DIR', log_dir), \
             unittest.mock.patch('treekit.builder._LOG_FILE', log_file), \
             pytest.raises(SystemExit):
            run_main(['treekit', str(spec), '--output', str(tmp_path)], monkeypatch)

        assert (tmp_path / 'simple_project').is_dir()
        assert (tmp_path / 'simple_project' / 'src').is_dir()
        assert (tmp_path / 'simple_project' / 'src' / 'main.py').is_file()
        assert (tmp_path / 'simple_project' / 'README.md').is_file()

    def test_file_input_summary_to_stdout(self, tmp_path, monkeypatch, capsys):
        """Build summary is printed to stdout."""
        spec = tmp_path / 'structure.md'
        spec.write_text(SIMPLE_MARKDOWN, encoding='utf-8')

        log_dir = tmp_path / 'log'
        log_file = log_dir / 'treekit.log'

        with unittest.mock.patch('treekit.builder._LOG_DIR', log_dir), \
             unittest.mock.patch('treekit.builder._LOG_FILE', log_file), \
             pytest.raises(SystemExit):
            run_main(['treekit', str(spec), '--output', str(tmp_path)], monkeypatch)

        out = capsys.readouterr().out
        assert 'simple_project' in out


# -----------------------------------------------------------------------------
# Stdin input
# -----------------------------------------------------------------------------

class TestStdinInput:
    """CLI reads from stdin when no file argument is given."""

    def test_stdin_input_exits_zero(self, tmp_path, monkeypatch, capsys):
        """Piped stdin input produces exit 0."""
        log_dir = tmp_path / 'log'
        log_file = log_dir / 'treekit.log'

        mock_stdin = unittest.mock.MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = SIMPLE_MARKDOWN

        with unittest.mock.patch('treekit.builder._LOG_DIR', log_dir), \
             unittest.mock.patch('treekit.builder._LOG_FILE', log_file), \
             unittest.mock.patch('sys.stdin', mock_stdin), \
             pytest.raises(SystemExit) as exc_info:
            run_main(['treekit', '--output', str(tmp_path)], monkeypatch)

        assert exc_info.value.code == 0

    def test_stdin_creates_structure(self, tmp_path, monkeypatch, capsys):
        """Piped stdin input creates the expected directory structure."""
        log_dir = tmp_path / 'log'
        log_file = log_dir / 'treekit.log'

        mock_stdin = unittest.mock.MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = SIMPLE_MARKDOWN

        with unittest.mock.patch('treekit.builder._LOG_DIR', log_dir), \
             unittest.mock.patch('treekit.builder._LOG_FILE', log_file), \
             unittest.mock.patch('sys.stdin', mock_stdin), \
             pytest.raises(SystemExit):
            run_main(['treekit', '--output', str(tmp_path)], monkeypatch)

        assert (tmp_path / 'simple_project').is_dir()

    def test_stdin_tty_with_no_file_exits_two(self, tmp_path, monkeypatch, capsys):
        """Interactive terminal stdin with no file argument exits with code 2."""
        mock_stdin = unittest.mock.MagicMock()
        mock_stdin.isatty.return_value = True

        with unittest.mock.patch('sys.stdin', mock_stdin), \
             pytest.raises(SystemExit) as exc_info:
            run_main(['treekit', '--output', str(tmp_path)], monkeypatch)

        assert exc_info.value.code == 2

    def test_stdin_tty_error_message(self, tmp_path, monkeypatch, capsys):
        """Error message is printed to stderr when stdin is a tty."""
        mock_stdin = unittest.mock.MagicMock()
        mock_stdin.isatty.return_value = True

        with unittest.mock.patch('sys.stdin', mock_stdin), \
             pytest.raises(SystemExit):
            run_main(['treekit', '--output', str(tmp_path)], monkeypatch)

        err = capsys.readouterr().err
        assert 'treekit: error:' in err


# -----------------------------------------------------------------------------
# --dry-run flag
# -----------------------------------------------------------------------------

class TestDryRunFlag:
    """--dry-run flag passes dry_run=True to the builder."""

    def test_dry_run_nothing_created(self, tmp_path, monkeypatch, capsys):
        """--dry-run creates nothing on disk."""
        spec = tmp_path / 'structure.md'
        spec.write_text(SIMPLE_MARKDOWN, encoding='utf-8')

        log_dir = tmp_path / 'log'
        log_file = log_dir / 'treekit.log'

        # Decline confirmation
        with unittest.mock.patch('treekit.builder._LOG_DIR', log_dir), \
             unittest.mock.patch('treekit.builder._LOG_FILE', log_file), \
             unittest.mock.patch('builtins.input', return_value='n'), \
             pytest.raises(SystemExit):
            run_main(
                ['treekit', str(spec), '--output', str(tmp_path), '--dry-run'],
                monkeypatch,
            )

        assert not (tmp_path / 'simple_project').exists()

    def test_dry_run_confirmed_creates_structure(self, tmp_path, monkeypatch, capsys):
        """--dry-run followed by 'y' confirmation creates the structure."""
        spec = tmp_path / 'structure.md'
        spec.write_text(SIMPLE_MARKDOWN, encoding='utf-8')

        log_dir = tmp_path / 'log'
        log_file = log_dir / 'treekit.log'

        with unittest.mock.patch('treekit.builder._LOG_DIR', log_dir), \
             unittest.mock.patch('treekit.builder._LOG_FILE', log_file), \
             unittest.mock.patch('builtins.input', return_value='y'), \
             pytest.raises(SystemExit):
            run_main(
                ['treekit', str(spec), '--output', str(tmp_path), '--dry-run'],
                monkeypatch,
            )

        assert (tmp_path / 'simple_project').is_dir()

    def test_dry_run_prints_would_create(self, tmp_path, monkeypatch, capsys):
        """--dry-run prints the list of paths that would be created."""
        spec = tmp_path / 'structure.md'
        spec.write_text(SIMPLE_MARKDOWN, encoding='utf-8')

        log_dir = tmp_path / 'log'
        log_file = log_dir / 'treekit.log'

        with unittest.mock.patch('treekit.builder._LOG_DIR', log_dir), \
             unittest.mock.patch('treekit.builder._LOG_FILE', log_file), \
             unittest.mock.patch('builtins.input', return_value='n'), \
             pytest.raises(SystemExit):
            run_main(
                ['treekit', str(spec), '--output', str(tmp_path), '--dry-run'],
                monkeypatch,
            )

        out = capsys.readouterr().out
        assert 'Would create' in out
        assert 'simple_project' in out

    def test_dry_run_aborted_exits_zero(self, tmp_path, monkeypatch, capsys):
        """Declining dry-run confirmation exits with code 0."""
        spec = tmp_path / 'structure.md'
        spec.write_text(SIMPLE_MARKDOWN, encoding='utf-8')

        log_dir = tmp_path / 'log'
        log_file = log_dir / 'treekit.log'

        with unittest.mock.patch('treekit.builder._LOG_DIR', log_dir), \
             unittest.mock.patch('treekit.builder._LOG_FILE', log_file), \
             unittest.mock.patch('builtins.input', return_value='n'), \
             pytest.raises(SystemExit) as exc_info:
            run_main(
                ['treekit', str(spec), '--output', str(tmp_path), '--dry-run'],
                monkeypatch,
            )

        assert exc_info.value.code == 0


# -----------------------------------------------------------------------------
# Error cases
# -----------------------------------------------------------------------------

class TestErrorCases:
    """CLI handles error conditions cleanly."""

    def test_missing_file_exits_one(self, tmp_path, monkeypatch, capsys):
        """Non-existent input file exits with code 1."""
        with pytest.raises(SystemExit) as exc_info:
            run_main(
                ['treekit', str(tmp_path / 'does_not_exist.md'), '--output', str(tmp_path)],
                monkeypatch,
            )
        assert exc_info.value.code == 1

    def test_missing_file_error_message(self, tmp_path, monkeypatch, capsys):
        """Non-existent input file prints error to stderr."""
        with pytest.raises(SystemExit):
            run_main(
                ['treekit', str(tmp_path / 'does_not_exist.md'), '--output', str(tmp_path)],
                monkeypatch,
            )
        err = capsys.readouterr().err
        assert 'treekit: error:' in err

    def test_empty_file_exits_one(self, tmp_path, monkeypatch, capsys):
        """Empty input file exits with code 1."""
        spec = tmp_path / 'empty.md'
        spec.write_text('', encoding='utf-8')

        with pytest.raises(SystemExit) as exc_info:
            run_main(
                ['treekit', str(spec), '--output', str(tmp_path)],
                monkeypatch,
            )
        assert exc_info.value.code == 1

    def test_no_tree_content_exits_one(self, tmp_path, monkeypatch, capsys):
        """File with no tree structure exits with code 1."""
        spec = tmp_path / 'prose.md'
        spec.write_text('# Just a heading\n\nSome prose text.\n', encoding='utf-8')

        with pytest.raises(SystemExit) as exc_info:
            run_main(
                ['treekit', str(spec), '--output', str(tmp_path)],
                monkeypatch,
            )
        assert exc_info.value.code == 1

    def test_parse_error_message_to_stderr(self, tmp_path, monkeypatch, capsys):
        """Parse failures print an error message to stderr."""
        spec = tmp_path / 'bad.md'
        spec.write_text('', encoding='utf-8')

        with pytest.raises(SystemExit):
            run_main(
                ['treekit', str(spec), '--output', str(tmp_path)],
                monkeypatch,
            )
        err = capsys.readouterr().err
        assert 'treekit: error:' in err


# -----------------------------------------------------------------------------
# LogError handling
# -----------------------------------------------------------------------------

class TestLogErrorHandling:
    """LogError prints a warning but does not cause a non-zero exit."""

    def test_log_error_exits_zero(self, tmp_path, monkeypatch, capsys):
        """Build succeeds and exits 0 even when log write fails."""
        spec = tmp_path / 'structure.md'
        spec.write_text(SIMPLE_MARKDOWN, encoding='utf-8')

        with unittest.mock.patch(
            'treekit.builder.TreeBuilder._write_log',
            side_effect=LogError("log failed"),
        ), pytest.raises(SystemExit) as exc_info:
            run_main(
                ['treekit', str(spec), '--output', str(tmp_path)],
                monkeypatch,
            )

        assert exc_info.value.code == 0

    def test_log_error_warning_to_stderr(self, tmp_path, monkeypatch, capsys):
        """A warning is printed to stderr when log write fails."""
        spec = tmp_path / 'structure.md'
        spec.write_text(SIMPLE_MARKDOWN, encoding='utf-8')

        with unittest.mock.patch(
            'treekit.builder.TreeBuilder._write_log',
            side_effect=LogError("log failed"),
        ), pytest.raises(SystemExit):
            run_main(
                ['treekit', str(spec), '--output', str(tmp_path)],
                monkeypatch,
            )

        err = capsys.readouterr().err
        assert 'treekit: warning:' in err
