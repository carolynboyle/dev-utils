# css_detector.py

**Path:** python/sniffkit/src/sniffkit/detectors/css_detector.py
**Syntax:** python
**Generated:** 2026-05-20 15:41:52

```python
"""
CSS content detector for sniffkit.

Scores text on the density and variety of CSS-specific syntax patterns.
Does not attempt to parse CSS — uses regex signal counting only.
"""

import re
from sniffkit.detectors import register, Detector


@register
class CssDetector:
    """Detects CSS content by heuristic pattern analysis."""

    type_label: str = "css"
    extension:  str = ".css"

    # Patterns that strongly suggest CSS
    _STRONG_SIGNALS = [
        re.compile(r'\{[^}]*\}'),              # rule blocks
        re.compile(r'@media\b'),               # media queries
        re.compile(r'@keyframes\b'),           # animations
        re.compile(r'@import\b'),              # imports
        re.compile(r':\s*(hover|focus|active|root|before|after)\b'),  # pseudo
    ]

    # Patterns that suggest CSS but also appear in other formats
    _WEAK_SIGNALS = [
        re.compile(r'[a-z-]+\s*:\s*[^;{}\n]+;'),  # property: value;
        re.compile(r'^\s*\.[a-z][\w-]*\s*\{', re.MULTILINE),   # .class {
        re.compile(r'^\s*#[a-z][\w-]*\s*\{', re.MULTILINE),    # #id {
        re.compile(r'^\s*[a-z][\w-]*\s*\{', re.MULTILINE),     # element {
    ]

    # Patterns that indicate this is NOT css
    _NEGATIVE_SIGNALS = [
        re.compile(r'<!DOCTYPE', re.IGNORECASE),
        re.compile(r'<html', re.IGNORECASE),
        re.compile(r'^\s*#{1,6}\s+\w', re.MULTILINE),   # markdown headings
        re.compile(r'SELECT\s+\w', re.IGNORECASE),
    ]

    def detect(self, text: str) -> float:
        """Return confidence score for CSS content."""
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

        # Density bonus: if { and } appear frequently relative to line count
        lines = text.splitlines()
        if lines:
            brace_lines = sum(1 for line in lines if '{' in line or '}' in line)
            density = brace_lines / len(lines)
            if density > 0.15:
                score += 0.10

        return min(score, 1.0)
```
