"""
HTML content detector for sniffkit.

Scores text on the presence and density of HTML-specific syntax patterns.
Does not attempt to parse HTML — uses regex signal counting only.
"""

import re
from sniffkit.detectors import register, Detector


@register
class HtmlDetector:
    """Detects HTML content by heuristic pattern analysis."""

    type_label: str = "html"
    extension:  str = ".html"

    # Patterns that strongly suggest HTML
    _STRONG_SIGNALS = [
        re.compile(r'<!DOCTYPE\s+html', re.IGNORECASE),
        re.compile(r'<html[\s>]', re.IGNORECASE),
        re.compile(r'<head[\s>]', re.IGNORECASE),
        re.compile(r'<body[\s>]', re.IGNORECASE),
        re.compile(r'<title[\s>]', re.IGNORECASE),
    ]

    # Patterns that suggest HTML but also appear in other formats
    _WEAK_SIGNALS = [
        re.compile(r'<div[\s>]', re.IGNORECASE),
        re.compile(r'<span[\s>]', re.IGNORECASE),
        re.compile(r'<p[\s>]', re.IGNORECASE),
        re.compile(r'<a\s+href=', re.IGNORECASE),
        re.compile(r'class="[^"]*"'),
        re.compile(r'</\w+>'),                          # any closing tag
        re.compile(r'<meta\s', re.IGNORECASE),
        re.compile(r'<link\s', re.IGNORECASE),
        re.compile(r'<script[\s>]', re.IGNORECASE),
        re.compile(r'<style[\s>]', re.IGNORECASE),
    ]

    # Patterns that indicate this is NOT HTML
    _NEGATIVE_SIGNALS = [
        re.compile(r'^\s*#{1,6}\s+\w', re.MULTILINE),  # markdown headings
        re.compile(r'SELECT\s+\w+\s+FROM\b', re.IGNORECASE),
    ]

    def detect(self, text: str) -> float:
        """Return confidence score for HTML content."""
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

        # Density bonus: if closing tags appear frequently
        lines = text.splitlines()
        if lines:
            tag_lines = sum(1 for line in lines if re.search(r'</\w+>', line))
            density = tag_lines / len(lines)
            if density > 0.10:
                score += 0.10

        return min(score, 1.0)
