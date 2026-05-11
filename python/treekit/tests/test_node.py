"""
test_node.py — Tests for the Node dataclass.

Covers:
    - Default field values
    - add_child() behaviour
    - __eq__() structural comparison
    - __len__() child count
    - __repr__() output format
"""

import pytest

from treekit.node import Node


# -----------------------------------------------------------------------------
# Construction
# -----------------------------------------------------------------------------

class TestNodeConstruction:
    """Node instantiation and default field values."""

    def test_required_fields(self):
        """Node can be created with required fields only."""
        node = Node(name='src', is_dir=True, depth=0)
        assert node.name == 'src'
        assert node.is_dir is True
        assert node.depth == 0

    def test_children_default_empty(self):
        """Children list defaults to empty, not shared across instances."""
        node_a = Node(name='a', is_dir=True, depth=0)
        node_b = Node(name='b', is_dir=True, depth=0)
        assert node_a.children == []
        assert node_b.children == []
        node_a.children.append(Node(name='child', is_dir=False, depth=1))
        assert node_b.children == []

    def test_comment_defaults_none(self):
        """Comment defaults to None when not supplied."""
        node = Node(name='main.py', is_dir=False, depth=1)
        assert node.comment is None

    def test_comment_stored(self):
        """Comment is stored when supplied."""
        node = Node(name='core.py', is_dir=False, depth=1, comment='Core module')
        assert node.comment == 'Core module'

    def test_file_node(self):
        """is_dir is False for file nodes."""
        node = Node(name='README.md', is_dir=False, depth=1)
        assert node.is_dir is False

    def test_depth_stored(self):
        """Depth value is stored correctly."""
        node = Node(name='nested', is_dir=True, depth=3)
        assert node.depth == 3


# -----------------------------------------------------------------------------
# add_child
# -----------------------------------------------------------------------------

class TestAddChild:
    """add_child() appends children in order."""

    def test_add_single_child(self):
        """A single child is appended correctly."""
        parent = Node(name='src', is_dir=True, depth=0)
        child = Node(name='main.py', is_dir=False, depth=1)
        parent.add_child(child)
        assert len(parent.children) == 1
        assert parent.children[0] is child

    def test_add_multiple_children_preserves_order(self):
        """Multiple children are stored in insertion order."""
        parent = Node(name='src', is_dir=True, depth=0)
        names = ['alpha.py', 'beta.py', 'gamma.py']
        for name in names:
            parent.add_child(Node(name=name, is_dir=False, depth=1))
        assert [c.name for c in parent.children] == names

    def test_children_are_independent_per_instance(self):
        """Adding a child to one node does not affect another."""
        parent_a = Node(name='a', is_dir=True, depth=0)
        parent_b = Node(name='b', is_dir=True, depth=0)
        parent_a.add_child(Node(name='child', is_dir=False, depth=1))
        assert len(parent_b.children) == 0


# -----------------------------------------------------------------------------
# __eq__
# -----------------------------------------------------------------------------

class TestNodeEquality:
    """__eq__() structural comparison."""

    def test_equal_leaf_nodes(self):
        """Two leaf nodes with identical fields are equal."""
        node_a = Node(name='main.py', is_dir=False, depth=1)
        node_b = Node(name='main.py', is_dir=False, depth=1)
        assert node_a == node_b

    def test_different_name_not_equal(self):
        """Nodes with different names are not equal."""
        node_a = Node(name='main.py', is_dir=False, depth=1)
        node_b = Node(name='core.py', is_dir=False, depth=1)
        assert node_a != node_b

    def test_different_is_dir_not_equal(self):
        """A file node and a directory node with the same name are not equal."""
        node_a = Node(name='src', is_dir=True, depth=0)
        node_b = Node(name='src', is_dir=False, depth=0)
        assert node_a != node_b

    def test_different_depth_not_equal(self):
        """Nodes at different depths are not equal."""
        node_a = Node(name='main.py', is_dir=False, depth=1)
        node_b = Node(name='main.py', is_dir=False, depth=2)
        assert node_a != node_b

    def test_different_comment_not_equal(self):
        """Nodes with different comments are not equal."""
        node_a = Node(name='core.py', is_dir=False, depth=1, comment='Core module')
        node_b = Node(name='core.py', is_dir=False, depth=1, comment=None)
        assert node_a != node_b

    def test_equal_with_children(self):
        """Nodes with identical children trees are equal."""
        def make_tree():
            root = Node(name='src', is_dir=True, depth=0)
            root.add_child(Node(name='main.py', is_dir=False, depth=1))
            return root
        assert make_tree() == make_tree()

    def test_different_children_not_equal(self):
        """Nodes with different children are not equal."""
        root_a = Node(name='src', is_dir=True, depth=0)
        root_a.add_child(Node(name='main.py', is_dir=False, depth=1))

        root_b = Node(name='src', is_dir=True, depth=0)
        root_b.add_child(Node(name='core.py', is_dir=False, depth=1))

        assert root_a != root_b

    def test_not_equal_to_non_node(self):
        """Comparing a Node to a non-Node returns NotImplemented."""
        node = Node(name='main.py', is_dir=False, depth=1)
        result = node.__eq__('not a node')
        assert result is NotImplemented


# -----------------------------------------------------------------------------
# __len__
# -----------------------------------------------------------------------------

class TestNodeLen:
    """__len__() returns direct child count."""

    def test_empty_node_len_zero(self):
        """A node with no children has length zero."""
        node = Node(name='src', is_dir=True, depth=0)
        assert len(node) == 0

    def test_len_matches_child_count(self):
        """Length matches the number of children added."""
        parent = Node(name='src', is_dir=True, depth=0)
        for i in range(3):
            parent.add_child(Node(name=f'file_{i}.py', is_dir=False, depth=1))
        assert len(parent) == 3

    def test_len_does_not_count_grandchildren(self):
        """Length counts only direct children, not grandchildren."""
        root = Node(name='root', is_dir=True, depth=0)
        child = Node(name='child', is_dir=True, depth=1)
        child.add_child(Node(name='grandchild.py', is_dir=False, depth=2))
        root.add_child(child)
        assert len(root) == 1


# -----------------------------------------------------------------------------
# __repr__
# -----------------------------------------------------------------------------

class TestNodeRepr:
    """__repr__() output format."""

    def test_repr_directory(self):
        """Directory node repr includes 'dir' label."""
        node = Node(name='src', is_dir=True, depth=0)
        assert repr(node) == "Node('src', dir, depth=0)"

    def test_repr_file(self):
        """File node repr includes 'file' label."""
        node = Node(name='main.py', is_dir=False, depth=2)
        assert repr(node) == "Node('main.py', file, depth=2)"
