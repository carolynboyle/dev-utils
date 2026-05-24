"""
SQL content detector for sniffkit.

Scores text on the presence of SQL keywords and statement patterns.
Does not attempt to parse SQL — uses regex signal counting only.
"""

import re
from sniffkit.detectors import register, Detector


@register
class SqlDetector:
    """Detects SQL content by heuristic pattern analysis."""

    type_label: str = "sql"
    extension:  str = ".sql"

    # Patterns that strongly suggest SQL
    _STRONG_SIGNALS = [
        re.compile(r'\bSELECT\s+.+\s+FROM\b', re.IGNORECASE),
        re.compile(r'\bCREATE\s+TABLE\b', re.IGNORECASE),
        re.compile(r'\bINSERT\s+INTO\b', re.IGNORECASE),
        re.compile(r'\bDROP\s+TABLE\b', re.IGNORECASE),
        re.compile(r'\bALTER\s+TABLE\b', re.IGNORECASE),
        re.compile(r'\bCREATE\s+INDEX\b', re.IGNORECASE),
        re.compile(r'\bCREATE\s+VIEW\b', re.IGNORECASE),
    ]

    # Patterns that suggest SQL but also appear in other formats
    _WEAK_SIGNALS = [
        re.compile(r'\bWHERE\s+\w', re.IGNORECASE),
        re.compile(r'\bJOIN\s+\w', re.IGNORECASE),
        re.compile(r'\bGROUP\s+BY\b', re.IGNORECASE),
        re.compile(r'\bORDER\s+BY\b', re.IGNORECASE),
        re.compile(r'\bHAVING\b', re.IGNORECASE),
        re.compile(r'^\s*--\s+\w', re.MULTILINE),              # SQL line comments
        re.compile(r';\s*$', re.MULTILINE),                    # statement terminators
        re.compile(r'\bPRIMARY\s+KEY\b', re.IGNORECASE),
        re.compile(r'\bFOREIGN\s+KEY\b', re.IGNORECASE),
        re.compile(r'\bNOT\s+NULL\b', re.IGNORECASE),
    ]

    # Patterns that indicate this is NOT SQL
    _NEGATIVE_SIGNALS = [
        re.compile(r'<!DOCTYPE', re.IGNORECASE),
        re.compile(r'<html', re.IGNORECASE),
        re.compile(r'^\s*#{1,6}\s+\w', re.MULTILINE),          # markdown headings
    ]

    def detect(self, text: str) -> float:
        """Return confidence score for SQL content."""
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

        # Density bonus: semicolon-terminated lines relative to total
        lines = text.splitlines()
        if lines:
            terminated = sum(1 for line in lines if re.search(r';\s*$', line))
            density = terminated / len(lines)
            if density > 0.10:
                score += 0.10

        return min(score, 1.0)
