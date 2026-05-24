# md_detector.py

**Path:** python/sniffkit/src/sniffkit/detectors/md_detector.py
**Syntax:** python
**Generated:** 2026-05-20 15:41:52

```python
"""
Markdown content detector for sniffkit.

Scores text on the presence and density of Markdown-specific syntax patterns.
Does not attempt to parse Markdown — uses regex signal counting only.
"""

import re
from sniffkit.detectors import register, Detector


@register
class MdDetector:
    """Detects Markdown content by heuristic pattern analysis."""

    type_label: str = "md"
    extension:  str = ".md"

    # Patterns that strongly suggest Markdown
    _STRONG_SIGNALS = [
        re.compile(r'^\s*#{1,6}\s+\w', re.MULTILINE),          # ATX headings
        re.compile(r'^[^\n]+\n[=]{3,}\s*$', re.MULTILINE),     # setext heading ==
        re.compile(r'^[^\n]+\n[-]{3,}\s*$', re.MULTILINE),     # setext heading --
        re.compile(r'^```', re.MULTILINE),                      # fenced code block
        re.compile(r'^\s*~~~', re.MULTILINE),                   # fenced code block alt
        re.compile(r'\[.+?\]\(.+?\)'),                          # [text](url) link
    ]

    # Patterns that suggest Markdown but also appear in other formats
    _WEAK_SIGNALS = [
        re.compile(r'\*\*.+?\*\*'),                             # **bold**
        re.compile(r'\*.+?\*'),                                 # *italic*
        re.compile(r'^\s*[-*+]\s+\w', re.MULTILINE),           # unordered list
        re.compile(r'^\s*\d+\.\s+\w', re.MULTILINE),           # ordered list
        re.compile(r'^\s*>\s+\w', re.MULTILINE),               # blockquote
        re.compile(r'^\|.+\|.+\|', re.MULTILINE),              # table row
        re.compile(r'^\s*---+\s*$', re.MULTILINE),             # horizontal rule
        re.compile(r'`[^`]+`'),                                 # inline code
    ]

    # Patterns that indicate this is NOT Markdown
    _NEGATIVE_SIGNALS = [
        re.compile(r'<!DOCTYPE', re.IGNORECASE),
        re.compile(r'<html', re.IGNORECASE),
        re.compile(r'SELECT\s+\w+\s+FROM\b', re.IGNORECASE),
    ]

    def detect(self, text: str) -> float:
        """Return confidence score for Markdown content."""
        if not text or not text.strip():
            return 0.0

        # Immediate disqualification
        for pattern in self._NEGATIVE_SIGNALS:
            if pattern.search(text):
                return 0.0

        score = 0.0

        # Strong signals: 0.25 each, capped at 0.50
        strong_hits = sum(
            1 for p in self._STRONG_SIGNALS if p.search(text)
        )
        score += min(strong_hits * 0.25, 0.50)

        # Weak signals: 0.10 each, capped at 0.40
        weak_hits = sum(
            1 for p in self._WEAK_SIGNALS if p.search(text)
        )
        score += min(weak_hits * 0.10, 0.40)

        # Density bonus: heading lines relative to total lines
        lines = text.splitlines()
        if lines:
            heading_lines = sum(
                1 for line in lines if re.match(r'^\s*#{1,6}\s+\w', line)
            )
            density = heading_lines / len(lines)
            if density > 0.05:
                score += 0.10

        return min(score, 1.0)

```
