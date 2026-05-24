"""
JSON content detector for sniffkit.

Attempts json.loads() first — a successful parse is unambiguous.
Falls back to heuristic scoring if parsing fails.
Does not modify the text or perform any I/O.
"""

import json
import re
from sniffkit.detectors import register, Detector


@register
class JsonDetector:
    """Detects JSON content by parse attempt then heuristic pattern analysis."""

    type_label: str = "json"
    extension:  str = ".json"

    # Patterns that strongly suggest JSON (heuristic fallback only)
    _STRONG_SIGNALS = [
        re.compile(r'^\s*[\[{]'),                       # starts with [ or {
        re.compile(r'"\w[\w\s]*"\s*:'),                 # "key": pattern
        re.compile(r'[\]}\s]$'),                        # ends with ] or }
    ]

    # Patterns that suggest JSON but also appear elsewhere
    _WEAK_SIGNALS = [
        re.compile(r':\s*(true|false|null)\b'),         # JSON literals
        re.compile(r':\s*-?\d+(\.\d+)?'),               # numeric values
        re.compile(r'",\s*"'),                          # adjacent string values
    ]

    # Patterns that indicate this is NOT JSON
    _NEGATIVE_SIGNALS = [
        re.compile(r'<!DOCTYPE', re.IGNORECASE),
        re.compile(r'<html', re.IGNORECASE),
        re.compile(r'SELECT\s+\w+\s+FROM\b', re.IGNORECASE),
        re.compile(r'^\s*#{1,6}\s+\w', re.MULTILINE),  # markdown headings
    ]

    def detect(self, text: str) -> float:
        """
        Return confidence score for JSON content.

        Attempts json.loads() first. If the entire text parses as a
        dict or list, returns 1.0 immediately. Falls back to heuristic
        scoring on parse failure.
        """
        if not text or not text.strip():
            return 0.0

        # Immediate disqualification
        for pattern in self._NEGATIVE_SIGNALS:
            if pattern.search(text):
                return 0.0

        # Definitive parse attempt — unambiguous if successful
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, (dict, list)):
                return 1.0
        except (json.JSONDecodeError, ValueError):
            pass

        # Heuristic fallback
        score = 0.0

        # Strong signals: 0.25 each, capped at 0.50
        strong_hits = sum(
            1 for p in self._STRONG_SIGNALS if p.search(text)
        )
        score += min(strong_hits * 0.25, 0.50)

        # Weak signals: 0.10 each, capped at 0.30
        weak_hits = sum(
            1 for p in self._WEAK_SIGNALS if p.search(text)
        )
        score += min(weak_hits * 0.10, 0.30)

        return min(score, 1.0)
