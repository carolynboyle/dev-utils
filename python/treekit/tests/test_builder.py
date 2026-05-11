"""
test_builder.py — Tests for TreeBuilder and BuildResult.

Covers:
    - Dry run: correct paths collected, nothing created on disk
    - Live run: directories and files created under tmp_path
    - Existing directory skipped cleanly
    - Existing file skipped cleanly
    - PathCollisionError: file where directory expected
    - PathCollisionError: directory where file expected
    - OutputPathError: output path does not exist
    - OutputPathError: output path is a file, not a directory
    - Log written correctly after successful build
    - Log written correctly after dry run
    - Log appends across multiple runs
    - LogError raised when log directory is unwriteable
    - BuildResult.success property
"""

import stat
import unittest.mock
from pathlib import Path

import pytest

from treekit.builder import BuildResult, TreeBuilder, _LOG_DIR, _LOG_FILE
from treekit.exceptions import BuildError, LogError, OutputPathError, PathCollisionError
from treekit.node import Node


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def make_simple_tree() -> Node:
    """
    Build a minimal Node tree for builder tests.

        simple_project/
        ├── src/
        │   └── main.py
        └── README.md
    """
    root = Node(name='simple_project', is_dir=True, depth=0)
    src = Node(name='src', is_dir=True, depth=1)
    src.add_child(Node(name='main.py', is_dir=False, depth=2))
    root.add_child(src)
    root.add_child(Node(name='README.md', is_dir=False, depth=1))
    return root


@pytest.fixture
def simple_tree() -> Node:
    """Minimal Node tree for builder tests."""
    return make_simple_tree()


@pytest.fixture
def log_paths(tmp_path):
    """
    Patch _LOG_DIR and _LOG_FILE in builder to point at tmp_path.

    Yields (log_dir, log_file) for assertions.
    """
    log_dir = tmp_path / 'treekit_log'
    log_file = log_dir / 'treekit.log'
    with unittest.mock.patch('treekit.builder._LOG_DIR', log_dir), \
         unittest.mock.patch('treekit.builder._LOG_FILE', log_file):
        yield log_dir, log_file


# -----------------------------------------------------------------------------
# BuildResult
# -----------------------------------------------------------------------------

class TestBuildResult:
    """BuildResult dataclass behaviour."""

    def test_success_true_when_no_errors(self):
        """success is True when errors list is empty."""
        result = BuildResult(source='test.md', output=Path('/tmp'), dry_run=False)
        assert result.success is True

    def test_success_false_when_errors_present(self):
        """success is False when errors list is non-empty."""
        result = BuildResult(source='test.md', output=Path('/tmp'), dry_run=False)
        result.errors.append(('some/path', 'something went wrong'))
        assert result.success is False

    def test_lists_default_empty(self):
        """created, skipped, and errors default to empty lists."""
        result = BuildResult(source='test.md', output=Path('/tmp'), dry_run=False)
        assert result.created == []
        assert result.skipped == []
        assert result.errors == []

    def test_lists_independent_across_instances(self):
        """List fields are not shared between BuildResult instances."""
        result_a = BuildResult(source='a.md', output=Path('/tmp'), dry_run=False)
        result_b = BuildResult(source='b.md', output=Path('/tmp'), dry_run=False)
        result_a.created.append('some/path/')
        assert result_b.created == []


# -----------------------------------------------------------------------------
# Dry run
# -----------------------------------------------------------------------------

class TestDryRun:
    """Dry run collects paths without touching the filesystem."""

    def test_dry_run_nothing_created_on_disk(self, tmp_path, simple_tree, log_paths):
        """No files or directories are created during a dry run."""
        builder = TreeBuilder(output_path=tmp_path, dry_run=True, source='test.md')
        builder.build(simple_tree)
        project_dir = tmp_path / 'simple_project'
        assert not project_dir.exists()

    def test_dry_run_collects_directories(self, tmp_path, simple_tree, log_paths):
        """Dry run records directory paths with trailing slash."""
        builder = TreeBuilder(output_path=tmp_path, dry_run=True, source='test.md')
        result = builder.build(simple_tree)
        assert 'simple_project/' in result.created
        assert 'simple_project/src/' in result.created

    def test_dry_run_collects_files(self, tmp_path, simple_tree, log_paths):
        """Dry run records file paths without trailing slash."""
        builder = TreeBuilder(output_path=tmp_path, dry_run=True, source='test.md')
        result = builder.build(simple_tree)
        assert 'simple_project/src/main.py' in result.created
        assert 'simple_project/README.md' in result.created

    def test_dry_run_skipped_empty(self, tmp_path, simple_tree, log_paths):
        """Dry run records nothing in skipped."""
        builder = TreeBuilder(output_path=tmp_path, dry_run=True, source='test.md')
        result = builder.build(simple_tree)
        assert result.skipped == []

    def test_dry_run_flag_in_result(self, tmp_path, simple_tree, log_paths):
        """BuildResult reflects dry_run=True."""
        builder = TreeBuilder(output_path=tmp_path, dry_run=True, source='test.md')
        result = builder.build(simple_tree)
        assert result.dry_run is True


# -----------------------------------------------------------------------------
# Live build
# -----------------------------------------------------------------------------

class TestLiveBuild:
    """Live build creates the correct filesystem structure."""

    def test_root_directory_created(self, tmp_path, simple_tree, log_paths):
        """Root directory is created under output_path."""
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        builder.build(simple_tree)
        assert (tmp_path / 'simple_project').is_dir()

    def test_nested_directory_created(self, tmp_path, simple_tree, log_paths):
        """Nested directories are created correctly."""
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        builder.build(simple_tree)
        assert (tmp_path / 'simple_project' / 'src').is_dir()

    def test_file_created(self, tmp_path, simple_tree, log_paths):
        """Files are created as empty files."""
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        builder.build(simple_tree)
        main_py = tmp_path / 'simple_project' / 'src' / 'main.py'
        assert main_py.is_file()
        assert main_py.stat().st_size == 0

    def test_all_paths_in_created(self, tmp_path, simple_tree, log_paths):
        """All created paths appear in BuildResult.created."""
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        result = builder.build(simple_tree)
        assert 'simple_project/' in result.created
        assert 'simple_project/src/' in result.created
        assert 'simple_project/src/main.py' in result.created
        assert 'simple_project/README.md' in result.created

    def test_dry_run_false_in_result(self, tmp_path, simple_tree, log_paths):
        """BuildResult reflects dry_run=False."""
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        result = builder.build(simple_tree)
        assert result.dry_run is False

    def test_source_label_in_result(self, tmp_path, simple_tree, log_paths):
        """Source label is stored in BuildResult."""
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='my_spec.md')
        result = builder.build(simple_tree)
        assert result.source == 'my_spec.md'

    def test_output_path_in_result(self, tmp_path, simple_tree, log_paths):
        """Resolved output path is stored in BuildResult."""
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        result = builder.build(simple_tree)
        assert result.output == tmp_path.resolve()


# -----------------------------------------------------------------------------
# Skip behaviour
# -----------------------------------------------------------------------------

class TestSkipBehaviour:
    """Already-existing paths are skipped cleanly."""

    def test_existing_directory_skipped(self, tmp_path, simple_tree, log_paths):
        """An existing directory is skipped, not re-created or errored."""
        (tmp_path / 'simple_project').mkdir()
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        result = builder.build(simple_tree)
        assert 'simple_project/' in result.skipped
        assert 'simple_project/' not in result.created

    def test_existing_file_skipped(self, tmp_path, simple_tree, log_paths):
        """An existing file is skipped, not overwritten or errored."""
        (tmp_path / 'simple_project').mkdir()
        (tmp_path / 'simple_project' / 'src').mkdir()
        readme = tmp_path / 'simple_project' / 'README.md'
        readme.write_text('existing content', encoding='utf-8')
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        result = builder.build(simple_tree)
        assert 'simple_project/README.md' in result.skipped
        assert readme.read_text(encoding='utf-8') == 'existing content'


# -----------------------------------------------------------------------------
# Collision errors
# -----------------------------------------------------------------------------

class TestCollisionErrors:
    """Type mismatches between expected and existing paths are recorded as errors."""

    def test_file_where_directory_expected(self, tmp_path, log_paths):
        """A file at a path expected to be a directory is recorded as an error."""
        # Place a file where src/ should go
        (tmp_path / 'simple_project').mkdir()
        (tmp_path / 'simple_project' / 'src').write_text('', encoding='utf-8')

        tree = make_simple_tree()
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        result = builder.build(tree)
        error_paths = [path for path, _ in result.errors]
        assert 'simple_project/src/' in error_paths

    def test_directory_where_file_expected(self, tmp_path, log_paths):
        """A directory at a path expected to be a file is recorded as an error."""
        (tmp_path / 'simple_project').mkdir()
        (tmp_path / 'simple_project' / 'README.md').mkdir()

        tree = make_simple_tree()
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        result = builder.build(tree)
        error_paths = [path for path, _ in result.errors]
        assert 'simple_project/README.md' in error_paths


# -----------------------------------------------------------------------------
# Output path errors
# -----------------------------------------------------------------------------

class TestOutputPathErrors:
    """Invalid output paths raise OutputPathError before any build work."""

    def test_missing_output_path_raises(self, tmp_path):
        """A non-existent output path raises OutputPathError."""
        missing = tmp_path / 'does_not_exist'
        builder = TreeBuilder(output_path=missing, dry_run=False, source='test.md')
        with pytest.raises(OutputPathError):
            builder.build(make_simple_tree())

    def test_file_as_output_path_raises(self, tmp_path):
        """A file passed as output path raises OutputPathError."""
        output_file = tmp_path / 'not_a_dir.txt'
        output_file.write_text('', encoding='utf-8')
        builder = TreeBuilder(output_path=output_file, dry_run=False, source='test.md')
        with pytest.raises(OutputPathError):
            builder.build(make_simple_tree())


# -----------------------------------------------------------------------------
# Log output
# -----------------------------------------------------------------------------

class TestLogOutput:
    """Log file is written correctly after each run."""

    def test_log_file_created(self, tmp_path, simple_tree, log_paths):
        """Log file is created after a successful build."""
        _, log_file = log_paths
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        builder.build(simple_tree)
        assert log_file.exists()

    def test_log_contains_source(self, tmp_path, simple_tree, log_paths):
        """Log entry contains the source label."""
        _, log_file = log_paths
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='my_spec.md')
        builder.build(simple_tree)
        content = log_file.read_text(encoding='utf-8')
        assert 'my_spec.md' in content

    def test_log_contains_output_path(self, tmp_path, simple_tree, log_paths):
        """Log entry contains the output path."""
        _, log_file = log_paths
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        builder.build(simple_tree)
        content = log_file.read_text(encoding='utf-8')
        assert str(tmp_path) in content

    def test_log_contains_created_paths(self, tmp_path, simple_tree, log_paths):
        """Log entry lists created paths."""
        _, log_file = log_paths
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        builder.build(simple_tree)
        content = log_file.read_text(encoding='utf-8')
        assert 'simple_project/' in content

    def test_log_dry_run_label(self, tmp_path, simple_tree, log_paths):
        """Log entry marks dry run correctly."""
        _, log_file = log_paths
        builder = TreeBuilder(output_path=tmp_path, dry_run=True, source='test.md')
        builder.build(simple_tree)
        content = log_file.read_text(encoding='utf-8')
        assert 'Dry-run:  yes' in content

    def test_log_live_run_label(self, tmp_path, simple_tree, log_paths):
        """Log entry marks live run correctly."""
        _, log_file = log_paths
        builder = TreeBuilder(output_path=tmp_path, dry_run=False, source='test.md')
        builder.build(simple_tree)
        content = log_file.read_text(encoding='utf-8')
        assert 'Dry-run:  no' in content

    def test_log_appends_across_runs(self, tmp_path, log_paths):
        """Multiple runs append to the same log file."""
        _, log_file = log_paths
        for i in range(3):
            builder = TreeBuilder(
                output_path=tmp_path,
                dry_run=True,
                source=f'run_{i}.md',
            )
            builder.build(make_simple_tree())
        content = log_file.read_text(encoding='utf-8')
        assert content.count('===') >= 6  # Opening + closing marker per run

    def test_log_error_raised_when_log_unwriteable(self, tmp_path, simple_tree):
        """LogError is raised when the log file cannot be written."""
        log_dir = tmp_path / 'treekit_log'
        log_dir.mkdir()
        log_file = log_dir / 'treekit.log'
        # Create log file and remove write permission
        log_file.write_text('', encoding='utf-8')
        log_file.chmod(stat.S_IREAD)

        with unittest.mock.patch('treekit.builder._LOG_DIR', log_dir), \
             unittest.mock.patch('treekit.builder._LOG_FILE', log_file):
            builder = TreeBuilder(output_path=tmp_path, dry_run=True, source='test.md')
            with pytest.raises(LogError):
                builder.build(simple_tree)

        # Restore permissions so tmp_path cleanup succeeds
        log_file.chmod(stat.S_IREAD | stat.S_IWRITE)
