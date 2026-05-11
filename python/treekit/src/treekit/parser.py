"""
parser.py — Markdown tree parser for treekit.

Parses a markdown document containing a directory tree structure into a
tree of Node objects. Handles tree-style code blocks and bare tree text.
Strips tree drawing characters, inline comments, and trailing slashes.

Typical usage:
    parser = TreeParser()
    root = parser.parse(text)
"""

import re
from typing import Optional

from treekit.exceptions import EmptyInputError, NoTreeFoundError, ParseError
from treekit.node import Node


# Characters used in tree drawing — stripped to measure and clean lines.
_TREE_CHARS = set('├└─│ ')

# Regex to detect tree drawing characters at the start of a line.
_TREE_LINE_RE = re.compile(r'^[│├└─\s]+')

# Width of one indent level in standard tree output.
_INDENT_WIDTH = 4


class TreeParser:
    """
    Parses markdown text containing a directory tree into a Node tree.

    The input may be:
      - A fenced code block (``` or ~~~) containing tree output.
      - Bare tree text with no fencing.

    The first non-blank, non-fenced line with a trailing '/' is treated
    as the root node. All subsequent lines are parsed as children.
    """

    def parse(self, text: str) -> Node:
        """
        Parse markdown text into a Node tree.

        Args:
            text: Full content of the markdown input.

        Returns:
            Root Node with the full tree attached.

        Raises:
            EmptyInputError:  Input is empty or contains only whitespace.
            NoTreeFoundError: Input contains content but no parseable tree.
            ParseError:       Input contains a tree block but it is malformed.
        """
        if not text or not text.strip():
            raise EmptyInputError("Input is empty.")

        lines = text.splitlines()
        tree_lines = self._extract_tree_block(lines)

        if not tree_lines:
            raise NoTreeFoundError("No recognisable tree structure found in input.")

        parsed = [self._parse_line(line) for line in tree_lines]
        parsed = [p for p in parsed if p is not None]

        if not parsed:
            raise ParseError("Tree block found but contained no parseable entries.")

        return self._build_tree(parsed)

    # -------------------------------------------------------------------------
    # Private methods
    # -------------------------------------------------------------------------

    def _extract_tree_block(self, lines: list[str]) -> list[str]:
        """
        Extract the tree content from the input lines.

        Looks for a fenced code block first. If none is found, falls back
        to collecting lines that contain tree drawing characters or look
        like filesystem paths.

        Args:
            lines: All lines from the input document.

        Returns:
            List of raw tree lines, without fence markers.
        """
        # --- Fenced code block (``` or ~~~) ----------------------------------
        fence_re = re.compile(r'^(`{3,}|~{3,})')
        inside_fence = False
        fence_marker = None
        block: list[str] = []

        for line in lines:
            match = fence_re.match(line.rstrip())
            if match:
                if not inside_fence:
                    inside_fence = True
                    fence_marker = match.group(1)[0]
                elif fence_marker and line.startswith(fence_marker):
                    inside_fence = False
                    if block:
                        return block
                continue
            if inside_fence:
                block.append(line)

        # Unclosed fence — return what we collected if non-empty.
        if block:
            return block

        # --- Bare tree (no fencing) ------------------------------------------
        # Collect lines that start with tree characters or look like a root dir.
        tree_lines: list[str] = []
        for line in lines:
            stripped = line.rstrip()
            if not stripped:
                continue
            if _TREE_LINE_RE.match(stripped) or self._looks_like_root(stripped):
                tree_lines.append(stripped)

        return tree_lines

    @staticmethod
    def _looks_like_root(line: str) -> bool:
        """
        Return True if the line looks like a bare root directory entry.

        A root entry has no tree-drawing prefix and ends with '/'.

        Args:
            line: A single stripped line from the input.

        Returns:
            True if the line appears to be a root directory name.
        """
        stripped = line.strip()
        return bool(stripped) and '/' in stripped and not _TREE_LINE_RE.match(stripped)

    def _parse_line(self, line: str) -> Optional[tuple[int, str, bool, Optional[str]]]:
        """
        Parse a single tree line into its components.

        Args:
            line: A raw line from the extracted tree block.

        Returns:
            Tuple of (depth, name, is_dir, comment), or None if the line
            should be skipped (blank or unparseable).
        """
        if not line.strip():
            return None

        # Measure depth from character position before stripping.
        depth = self._measure_depth(line)

        # Strip tree-drawing characters to get the raw entry.
        raw = _TREE_LINE_RE.sub('', line).strip()

        if not raw:
            return None

        # Split inline comment.
        comment: Optional[str] = None
        if '#' in raw:
            parts = raw.split('#', 1)
            raw = parts[0].strip()
            comment_text = parts[1].strip()
            comment = comment_text if comment_text else None

        if not raw:
            return None

        # Determine type and clean name.
        is_dir = raw.endswith('/')
        name = raw.rstrip('/')

        if not name:
            return None

        return (depth, name, is_dir, comment)

    @staticmethod
    def _measure_depth(line: str) -> int:
        """
        Measure the nesting depth of a tree line.

        Depth is determined by the number of indent units preceding the
        entry name. The root entry (no prefix) is depth 0.

        Args:
            line: A raw line from the tree block.

        Returns:
            Zero-based integer depth.
        """
        # Count leading characters that are tree drawing or whitespace.
        prefix = _TREE_LINE_RE.match(line)
        if not prefix:
            return 0
        prefix_len = len(prefix.group(0))
        # Each level occupies _INDENT_WIDTH characters.
        return max(0, prefix_len // _INDENT_WIDTH)

    @staticmethod
    def _build_tree(
        parsed: list[tuple[int, str, bool, Optional[str]]]
    ) -> Node:
        """
        Assemble a Node tree from a list of parsed line tuples.

        Uses a stack to track the current ancestry. When a line is deeper
        than the previous, it becomes a child of the current node. When
        shallower, the stack is unwound to the correct parent.

        Args:
            parsed: Ordered list of (depth, name, is_dir, comment) tuples.

        Returns:
            Root Node of the assembled tree.

        Raises:
            ParseError: If the first entry is not a directory (no valid root).
        """
        first_depth, first_name, first_is_dir, first_comment = parsed[0]

        if not first_is_dir:
            raise ParseError(
                f"Expected a root directory as the first entry, got file: {first_name!r}"
            )

        root = Node(
            name=first_name,
            is_dir=True,
            depth=first_depth,
            comment=first_comment,
        )

        # Stack holds (node, depth) pairs for ancestry tracking.
        stack: list[tuple[Node, int]] = [(root, first_depth)]

        for depth, name, is_dir, comment in parsed[1:]:
            node = Node(name=name, is_dir=is_dir, depth=depth, comment=comment)

            # Unwind stack to find the correct parent.
            while len(stack) > 1 and stack[-1][1] >= depth:
                stack.pop()

            parent = stack[-1][0]
            parent.add_child(node)

            if is_dir:
                stack.append((node, depth))

        return root
