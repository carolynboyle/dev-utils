"""
tests/test_detectors.py
~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for all five sniffkit content detectors.

Each detector is tested with:
  - a confident positive sample (score >= 0.6)
  - a clear negative sample (score == 0.0 via negative-signal disqualification)
  - a cross-contamination case (one type's content fed to another detector)
  - edge cases: empty string, whitespace-only

Run with:
    pytest tests/test_detectors.py -v
"""

import pytest
from sniffkit.detectors import get_registry
from sniffkit.detectors.css_detector import CssDetector
from sniffkit.detectors.html_detector import HtmlDetector
from sniffkit.detectors.json_detector import JsonDetector
from sniffkit.detectors.md_detector import MdDetector
from sniffkit.detectors.sql_detector import SqlDetector


# =============================================================================
# Fixtures — representative content samples
# =============================================================================

CSS_SAMPLE = """\
body {
    margin: 0;
    padding: 0;
    font-family: sans-serif;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
}

@media (max-width: 768px) {
    .container {
        padding: 0 1rem;
    }
}

h1 {
    color: #333;
    font-size: 2rem;
}
"""

HTML_SAMPLE = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Test Page</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>Hello World</h1>
        <p>This is a <a href="#">test paragraph</a>.</p>
        <span class="note">Note text</span>
    </div>
    <script src="app.js"></script>
</body>
</html>
"""

JSON_SAMPLE = """\
{
    "experiment_id": "exp_01",
    "model": "gemma4:e2b",
    "runs": [
        {"id": 1, "status": "complete", "tokens": 512},
        {"id": 2, "status": "failed",   "tokens": 0}
    ],
    "metadata": {
        "created_at": "2026-05-20",
        "version": "0.1.0"
    }
}
"""

MD_SAMPLE = """\
# Experiment Results

## Summary

This experiment evaluated **gemma4:e2b** on structured output tasks.

### Findings

- Model produced valid JSON in 80% of runs
- Calibrated refusal observed in edge cases
- No hallucinated API calls

```python
result = classifier.classify_file(path)
```

See [design doc](docs/design.md) for full methodology.
"""

SQL_SAMPLE = """\
-- Experiment run summary view
CREATE VIEW v_run_summary AS
SELECT
    r.id,
    r.experiment_id,
    r.run_id_string,
    r.model,
    r.status,
    r.token_count,
    e.title AS experiment_title
FROM runs r
JOIN experiments e ON e.id = r.experiment_id
WHERE r.status != 'skipped'
ORDER BY r.created_at DESC;

INSERT INTO runs (experiment_id, model, status)
VALUES ('exp_01', 'gemma4:e2b', 'complete');
"""

PLAIN_TEXT_SAMPLE = """\
This is just plain text.
No special syntax. No structure.
It could be a log file or a note.
The detector should not be confident about any type.
"""


# =============================================================================
# Registry
# =============================================================================

class TestRegistry:
    def test_all_five_detectors_registered(self):
        registry = get_registry()
        assert set(registry.keys()) == {"css", "html", "json", "md", "sql"}

    def test_registry_returns_copy(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is not r2

    def test_detector_classes_have_required_attributes(self):
        registry = get_registry()
        for label, cls in registry.items():
            assert hasattr(cls, "type_label"), f"{label} missing type_label"
            assert hasattr(cls, "extension"),  f"{label} missing extension"
            assert callable(getattr(cls, "detect", None)), f"{label} missing detect()"

    def test_extensions_start_with_dot(self):
        registry = get_registry()
        for label, cls in registry.items():
            assert cls.extension.startswith("."), \
                f"{label}.extension should start with '.', got: {cls.extension!r}"


# =============================================================================
# Edge cases — shared across all detectors
# =============================================================================

DETECTORS = [CssDetector, HtmlDetector, JsonDetector, MdDetector, SqlDetector]

@pytest.mark.parametrize("DetectorClass", DETECTORS)
class TestEdgeCases:
    def test_empty_string_returns_zero(self, DetectorClass):
        assert DetectorClass().detect("") == 0.0

    def test_whitespace_only_returns_zero(self, DetectorClass):
        assert DetectorClass().detect("   \n\t\n  ") == 0.0

    def test_score_in_range(self, DetectorClass):
        score = DetectorClass().detect(PLAIN_TEXT_SAMPLE)
        assert 0.0 <= score <= 1.0

    def test_returns_float(self, DetectorClass):
        score = DetectorClass().detect(CSS_SAMPLE)
        assert isinstance(score, float)


# =============================================================================
# CssDetector
# =============================================================================

class TestCssDetector:
    def setup_method(self):
        self.detector = CssDetector()

    def test_positive_css(self):
        score = self.detector.detect(CSS_SAMPLE)
        assert score >= 0.6, f"Expected >= 0.6 for CSS sample, got {score}"

    def test_html_disqualifies_css(self):
        score = self.detector.detect(HTML_SAMPLE)
        assert score == 0.0, f"Expected 0.0 for HTML fed to CSS detector, got {score}"

    def test_markdown_heading_disqualifies(self):
        score = self.detector.detect(MD_SAMPLE)
        assert score == 0.0

    def test_sql_select_disqualifies(self):
        score = self.detector.detect(SQL_SAMPLE)
        assert score == 0.0

    def test_media_query_is_strong_signal(self):
        text = "@media (max-width: 768px) { .foo { display: none; } }"
        score = self.detector.detect(text)
        assert score >= 0.25

    def test_rule_block_contributes(self):
        text = "body { color: red; }"
        score = self.detector.detect(text)
        assert score > 0.0

    def test_score_capped_at_one(self):
        # Pile on every signal type
        score = self.detector.detect(CSS_SAMPLE * 3)
        assert score <= 1.0


# =============================================================================
# HtmlDetector
# =============================================================================

class TestHtmlDetector:
    def setup_method(self):
        self.detector = HtmlDetector()

    def test_positive_html(self):
        score = self.detector.detect(HTML_SAMPLE)
        assert score >= 0.6, f"Expected >= 0.6 for HTML sample, got {score}"

    def test_doctype_alone_is_strong(self):
        score = self.detector.detect("<!DOCTYPE html>\n<html><body>hi</body></html>")
        assert score >= 0.5

    def test_markdown_headings_disqualify(self):
        score = self.detector.detect(MD_SAMPLE)
        assert score == 0.0

    def test_sql_select_disqualifies(self):
        score = self.detector.detect(SQL_SAMPLE)
        assert score == 0.0

    def test_closing_tags_density_bonus(self):
        # Dense closing tags should trigger density bonus
        text = "<div>\n</div>\n<p>\n</p>\n<span>\n</span>\n<ul>\n</ul>\n<li>\n</li>\n"
        score = self.detector.detect(text)
        assert score > 0.0

    def test_plain_text_low_score(self):
        score = self.detector.detect(PLAIN_TEXT_SAMPLE)
        assert score < 0.6

    def test_score_capped_at_one(self):
        score = self.detector.detect(HTML_SAMPLE * 3)
        assert score <= 1.0


# =============================================================================
# JsonDetector
# =============================================================================

class TestJsonDetector:
    def setup_method(self):
        self.detector = JsonDetector()

    def test_valid_json_object_scores_one(self):
        score = self.detector.detect(JSON_SAMPLE)
        assert score == 1.0, f"Expected 1.0 for valid JSON, got {score}"

    def test_valid_json_array_scores_one(self):
        text = '[{"id": 1}, {"id": 2}]'
        score = self.detector.detect(text)
        assert score == 1.0

    def test_json_scalar_not_one(self):
        # json.loads("42") succeeds but is not dict/list — falls to heuristic
        score = self.detector.detect("42")
        assert score < 1.0

    def test_html_disqualifies(self):
        score = self.detector.detect(HTML_SAMPLE)
        assert score == 0.0

    def test_sql_low_score(self):
        # SQL_SAMPLE uses multiline SELECT so the negative-signal regex
        # (single-line SELECT...FROM) doesn't fire. Detector scores from
        # heuristics but should stay well below the 0.6 threshold.
        score = self.detector.detect(SQL_SAMPLE)
        assert score < 0.6

    def test_markdown_headings_disqualify(self):
        score = self.detector.detect(MD_SAMPLE)
        assert score == 0.0

    def test_malformed_json_heuristic_fallback(self):
        # Looks like JSON but doesn't parse cleanly
        text = '{"key": "value", "broken: true}'
        score = self.detector.detect(text)
        # Should score above 0 from heuristics but not reach 1.0
        assert 0.0 < score < 1.0

    def test_plain_text_low_score(self):
        score = self.detector.detect(PLAIN_TEXT_SAMPLE)
        assert score < 0.6

    def test_score_capped_at_one(self):
        score = self.detector.detect(JSON_SAMPLE)
        assert score <= 1.0


# =============================================================================
# MdDetector
# =============================================================================

class TestMdDetector:
    def setup_method(self):
        self.detector = MdDetector()

    def test_positive_markdown(self):
        score = self.detector.detect(MD_SAMPLE)
        assert score >= 0.6, f"Expected >= 0.6 for MD sample, got {score}"

    def test_html_disqualifies(self):
        score = self.detector.detect(HTML_SAMPLE)
        assert score == 0.0

    def test_sql_select_disqualifies(self):
        score = self.detector.detect(SQL_SAMPLE)
        assert score == 0.0

    def test_atx_heading_is_strong_signal(self):
        text = "# Title\n\nSome content here.\n"
        score = self.detector.detect(text)
        assert score >= 0.25

    def test_fenced_code_block_is_strong_signal(self):
        text = "```python\nprint('hello')\n```\n"
        score = self.detector.detect(text)
        assert score >= 0.25

    def test_bold_and_list_contribute(self):
        text = "**Important:** \n- item one\n- item two\n"
        score = self.detector.detect(text)
        assert score > 0.0

    def test_heading_density_bonus(self):
        # Heading density bonus fires when heading lines > 5% of total.
        # This minimal fixture (3 headings in 6 lines = 50%) triggers the
        # bonus but only reaches ~0.35 total — strong signals cap at 0.25
        # (ATX pattern fires once), plus density bonus 0.10.
        # Test that the bonus contributes, not that it alone reaches threshold.
        text = "# H1\ncontent\n## H2\ncontent\n### H3\ncontent\n"
        score = self.detector.detect(text)
        assert score > 0.25

    def test_plain_text_low_score(self):
        score = self.detector.detect(PLAIN_TEXT_SAMPLE)
        assert score < 0.6

    def test_score_capped_at_one(self):
        score = self.detector.detect(MD_SAMPLE * 3)
        assert score <= 1.0


# =============================================================================
# SqlDetector
# =============================================================================

class TestSqlDetector:
    def setup_method(self):
        self.detector = SqlDetector()

    def test_positive_sql(self):
        score = self.detector.detect(SQL_SAMPLE)
        assert score >= 0.6, f"Expected >= 0.6 for SQL sample, got {score}"

    def test_html_disqualifies(self):
        score = self.detector.detect(HTML_SAMPLE)
        assert score == 0.0

    def test_markdown_headings_disqualify(self):
        score = self.detector.detect(MD_SAMPLE)
        assert score == 0.0

    def test_select_from_is_strong_signal(self):
        text = "SELECT id, name FROM users WHERE active = true;"
        score = self.detector.detect(text)
        assert score >= 0.25

    def test_create_table_is_strong_signal(self):
        text = "CREATE TABLE runs (id SERIAL PRIMARY KEY, status TEXT NOT NULL);"
        score = self.detector.detect(text)
        assert score >= 0.25

    def test_weak_signals_accumulate(self):
        text = (
            "WHERE id > 0\n"
            "JOIN experiments ON experiments.id = runs.experiment_id\n"
            "GROUP BY model\n"
            "ORDER BY created_at DESC\n"
            "HAVING count(*) > 1;\n"
        )
        score = self.detector.detect(text)
        assert score > 0.0

    def test_semicolon_density_bonus(self):
        # All lines are semicolon-terminated (100% density > 10% threshold)
        # so the density bonus fires. But SELECT N; has no FROM clause so
        # the strong signal regex doesn't match — only weak signals accumulate.
        # Test that the bonus contributes, not that it alone reaches threshold.
        text = (
            "SELECT 1;\n"
            "SELECT 2;\n"
            "SELECT 3;\n"
            "SELECT 4;\n"
            "SELECT 5;\n"
        )
        score = self.detector.detect(text)
        assert score > 0.10  # density bonus fired

    def test_plain_text_low_score(self):
        score = self.detector.detect(PLAIN_TEXT_SAMPLE)
        assert score < 0.6

    def test_score_capped_at_one(self):
        score = self.detector.detect(SQL_SAMPLE * 3)
        assert score <= 1.0


# =============================================================================
# Cross-contamination matrix
# Ensures each detector stays below threshold on other types' content
# =============================================================================

class TestCrossContamination:
    """
    Each detector should score < 0.6 when given another type's content,
    unless negative signals fire first (score == 0.0).
    """

    SAMPLES = {
        "css":  CSS_SAMPLE,
        "html": HTML_SAMPLE,
        "json": JSON_SAMPLE,
        "md":   MD_SAMPLE,
        "sql":  SQL_SAMPLE,
    }

    DETECTORS = {
        "css":  CssDetector,
        "html": HtmlDetector,
        "json": JsonDetector,
        "md":   MdDetector,
        "sql":  SqlDetector,
    }

    @pytest.mark.parametrize("detector_label,sample_label", [
        (d, s)
        for d in ["css", "html", "json", "md", "sql"]
        for s in ["css", "html", "json", "md", "sql"]
        if d != s
    ])
    def test_no_false_positives(self, detector_label, sample_label):
        detector = self.DETECTORS[detector_label]()
        sample   = self.SAMPLES[sample_label]
        score    = detector.detect(sample)
        assert score < 0.6, (
            f"{detector_label} detector scored {score:.2f} on {sample_label} content "
            f"(expected < 0.6)"
        )
