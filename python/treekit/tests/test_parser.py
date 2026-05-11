"""
test_parser.py — Tests for TreeParser.

Covers:
    - Fenced code block input (happy path)
    - Bare tree input (happy path)
    - Full tree comparison against expected_tree fixture
    - Root node properties
    - Correct depth assignment
    - Correct parent/child relationships
    - Comment stripping and storage
    - File vs directory identification
    - Blank lines ignored
    - Whitespace-only input → EmptyInputError
    - Empty string input → EmptyInputError
    - Content with no tree → NoTreeFoundError
    - First entry not a directory → ParseError
    - Comments on directory nodes
    - Deeply nested structures
    - Siblings at the same depth
"""

import pytest

from treekit.exceptions import EmptyInputError, NoTreeFoundError, ParseError
from treekit.node import Node
from treekit.parser import TreeParser


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def parser() -> TreeParser:
    """A fresh TreeParser instance for each test."""
    return TreeParser()


# -----------------------------------------------------------------------------
# Happy path — full tree comparison
# -----------------------------------------------------------------------------

class TestHappyPath:
    """Parser produces correct Node trees from valid input."""

    def test_fenced_markdown_matches_expected(self, parser, fenced_markdown, expected_tree):
        """Fenced code block input produces a tree equal to the expected fixture."""
        result = parser.parse(fenced_markdown)
        assert result == expected_tree

    def test_bare_markdown_matches_expected(self, parser, bare_markdown, expected_tree):
        """Bare tree input produces a tree equal to the expected fixture."""
        result = parser.parse(bare_markdown)
        assert result == expected_tree

    def test_fenced_and_bare_produce_same_tree(self, parser, fenced_markdown, bare_markdown):
        """Fenced and bare input from the same source produce identical trees."""
        fenced_result = parser.parse(fenced_markdown)
        bare_result = parser.parse(bare_markdown)
        assert fenced_result == bare_result


# -----------------------------------------------------------------------------
# Root node
# -----------------------------------------------------------------------------

class TestRootNode:
    """Root node properties are correctly parsed."""

    def test_root_name(self, parser, fenced_markdown):
        """Root node has the correct name."""
        root = parser.parse(fenced_markdown)
        assert root.name == 'test_project'

    def test_root_is_directory(self, parser, fenced_markdown):
        """Root node is a directory."""
        root = parser.parse(fenced_markdown)
        assert root.is_dir is True

    def test_root_depth_is_zero(self, parser, fenced_markdown):
        """Root node is at depth zero."""
        root = parser.parse(fenced_markdown)
        assert root.depth == 0

    def test_root_child_count(self, parser, fenced_markdown):
        """Root node has the correct number of direct children."""
        root = parser.parse(fenced_markdown)
        # src/, tests/, docs/, pyproject.toml
        assert len(root) == 4


# -----------------------------------------------------------------------------
# Depth assignment
# -----------------------------------------------------------------------------

class TestDepthAssignment:
    """Nodes are assigned correct depth values."""

    def test_top_level_children_depth_one(self, parser, fenced_markdown):
        """Direct children of root are at depth 1."""
        root = parser.parse(fenced_markdown)
        for child in root.children:
            assert child.depth == 1

    def test_nested_directory_depth(self, parser, fenced_markdown):
        """src/test_project/ is at depth 2."""
        root = parser.parse(fenced_markdown)
        src = next(c for c in root.children if c.name == 'src')
        inner = src.children[0]
        assert inner.name == 'test_project'
        assert inner.depth == 2

    def test_deeply_nested_file_depth(self, parser, fenced_markdown):
        """Files inside src/test_project/ are at depth 3."""
        root = parser.parse(fenced_markdown)
        src = next(c for c in root.children if c.name == 'src')
        inner = src.children[0]
        for child in inner.children:
            assert child.depth == 3


# -----------------------------------------------------------------------------
# Parent/child relationships
# -----------------------------------------------------------------------------

class TestParentChildRelationships:
    """Nodes are attached to the correct parents."""

    def test_src_children(self, parser, fenced_markdown):
        """src/ contains only test_project/."""
        root = parser.parse(fenced_markdown)
        src = next(c for c in root.children if c.name == 'src')
        assert len(src) == 1
        assert src.children[0].name == 'test_project'

    def test_inner_package_children(self, parser, fenced_markdown):
        """src/test_project/ contains __init__.py and core.py."""
        root = parser.parse(fenced_markdown)
        src = next(c for c in root.children if c.name == 'src')
        inner = src.children[0]
        child_names = [c.name for c in inner.children]
        assert '__init__.py' in child_names
        assert 'core.py' in child_names
        assert len(inner) == 2

    def test_tests_children(self, parser, fenced_markdown):
        """tests/ contains __init__.py and test_core.py."""
        root = parser.parse(fenced_markdown)
        tests = next(c for c in root.children if c.name == 'tests')
        child_names = [c.name for c in tests.children]
        assert '__init__.py' in child_names
        assert 'test_core.py' in child_names
        assert len(tests) == 2

    def test_docs_children(self, parser, fenced_markdown):
        """docs/ contains only README.md."""
        root = parser.parse(fenced_markdown)
        docs = next(c for c in root.children if c.name == 'docs')
        assert len(docs) == 1
        assert docs.children[0].name == 'README.md'

    def test_pyproject_is_child_of_root(self, parser, fenced_markdown):
        """pyproject.toml is a direct child of root."""
        root = parser.parse(fenced_markdown)
        child_names = [c.name for c in root.children]
        assert 'pyproject.toml' in child_names

    def test_child_order_preserved(self, parser, fenced_markdown):
        """Children are stored in source order."""
        root = parser.parse(fenced_markdown)
        child_names = [c.name for c in root.children]
        assert child_names == ['src', 'tests', 'docs', 'pyproject.toml']


# -----------------------------------------------------------------------------
# File vs directory identification
# -----------------------------------------------------------------------------

class TestFileDirectoryIdentification:
    """Trailing slash correctly identifies directories vs files."""

    def test_src_is_directory(self, parser, fenced_markdown):
        """src/ is identified as a directory."""
        root = parser.parse(fenced_markdown)
        src = next(c for c in root.children if c.name == 'src')
        assert src.is_dir is True

    def test_pyproject_is_file(self, parser, fenced_markdown):
        """pyproject.toml is identified as a file."""
        root = parser.parse(fenced_markdown)
        pyproject = next(c for c in root.children if c.name == 'pyproject.toml')
        assert pyproject.is_dir is False

    def test_init_py_is_file(self, parser, fenced_markdown):
        """__init__.py is identified as a file."""
        root = parser.parse(fenced_markdown)
        src = next(c for c in root.children if c.name == 'src')
        inner = src.children[0]
        init = next(c for c in inner.children if c.name == '__init__.py')
        assert init.is_dir is False

    def test_directory_name_has_no_trailing_slash(self, parser, fenced_markdown):
        """Directory nodes have trailing slash stripped from their name."""
        root = parser.parse(fenced_markdown)
        for child in root.children:
            assert not child.name.endswith('/')


# -----------------------------------------------------------------------------
# Comment handling
# -----------------------------------------------------------------------------

class TestCommentHandling:
    """Inline comments are stripped from names and stored separately."""

    def test_file_comment_stored(self, parser, fenced_markdown):
        """Comment on a file node is stored correctly."""
        root = parser.parse(fenced_markdown)
        src = next(c for c in root.children if c.name == 'src')
        inner = src.children[0]
        core = next(c for c in inner.children if c.name == 'core.py')
        assert core.comment == 'Core module'

    def test_directory_comment_stored(self, parser, fenced_markdown):
        """Comment on a directory node is stored correctly."""
        root = parser.parse(fenced_markdown)
        docs = next(c for c in root.children if c.name == 'docs')
        assert docs.comment == 'Documentation'

    def test_comment_not_in_name(self, parser, fenced_markdown):
        """Comment text does not appear in the node name."""
        root = parser.parse(fenced_markdown)
        src = next(c for c in root.children if c.name == 'src')
        inner = src.children[0]
        core = next(c for c in inner.children if c.name == 'core.py')
        assert '#' not in core.name
        assert 'Core module' not in core.name

    def test_no_comment_is_none(self, parser, fenced_markdown):
        """Nodes without comments have comment set to None."""
        root = parser.parse(fenced_markdown)
        pyproject = next(c for c in root.children if c.name == 'pyproject.toml')
        assert pyproject.comment is None


# -----------------------------------------------------------------------------
# Blank line handling
# -----------------------------------------------------------------------------

class TestBlankLineHandling:
    """Blank lines in the tree block are silently ignored."""

    def test_blank_lines_ignored(self, parser):
        """Blank lines between tree entries do not affect the result."""
        markdown = """\
```
test_project/

├── src/

│   └── main.py

└── README.md
```
"""
        root = parser.parse(markdown)
        assert root.name == 'test_project'
        assert len(root) == 2
        child_names = [c.name for c in root.children]
        assert 'src' in child_names
        assert 'README.md' in child_names


# -----------------------------------------------------------------------------
# Error cases
# -----------------------------------------------------------------------------

class TestErrorCases:
    """Parser raises correct exceptions for invalid input."""

    def test_empty_string_raises_empty_input_error(self, parser):
        """Empty string raises EmptyInputError."""
        with pytest.raises(EmptyInputError):
            parser.parse('')

    def test_whitespace_only_raises_empty_input_error(self, parser):
        """Whitespace-only input raises EmptyInputError."""
        with pytest.raises(EmptyInputError):
            parser.parse('   \n\n\t  \n')

    def test_no_tree_content_raises_no_tree_found_error(self, parser):
        """Markdown with no tree structure raises NoTreeFoundError."""
        markdown = """\
# My Project

This is a description of my project.

It has no tree structure at all.
"""
        with pytest.raises(NoTreeFoundError):
            parser.parse(markdown)

    def test_first_entry_not_directory_raises_parse_error(self, parser):
        """A tree whose first entry is a file raises ParseError."""
        markdown = """\
```
README.md
├── src/
└── main.py
```
"""
        with pytest.raises(ParseError):
            parser.parse(markdown)

    def test_empty_fenced_block_raises_no_tree_found_error(self, parser):
        """A fenced block containing only blank lines raises NoTreeFoundError."""
        markdown = """\
```

```
"""
        with pytest.raises((NoTreeFoundError, ParseError)):
            parser.parse(markdown)


# -----------------------------------------------------------------------------
# Siblings
# -----------------------------------------------------------------------------

class TestSiblings:
    """Nodes at the same depth under the same parent are siblings."""

    def test_siblings_attached_to_same_parent(self, parser):
        """Two entries at the same depth are siblings under the same parent."""
        markdown = """\
```
project/
├── alpha.py
└── beta.py
```
"""
        root = parser.parse(markdown)
        assert len(root) == 2
        child_names = [c.name for c in root.children]
        assert child_names == ['alpha.py', 'beta.py']

    def test_sibling_directories(self, parser):
        """Two directories at the same depth are siblings."""
        markdown = """\
```
project/
├── src/
└── tests/
```
"""
        root = parser.parse(markdown)
        assert len(root) == 2
        assert all(c.is_dir for c in root.children)


# -----------------------------------------------------------------------------
# Deep nesting
# -----------------------------------------------------------------------------

class TestDeepNesting:
    """Parser handles deep nesting correctly."""

    def test_three_levels_deep(self, parser):
        """A three-level deep file is correctly attached to its parent."""
        markdown = """\
```
project/
└── a/
    └── b/
        └── c.py
```
"""
        root = parser.parse(markdown)
        a = root.children[0]
        b = a.children[0]
        c = b.children[0]

        assert a.name == 'a'
        assert b.name == 'b'
        assert c.name == 'c.py'
        assert c.is_dir is False
        assert c.depth == 3
