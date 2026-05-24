"""
tests/test_classifier.py
~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for sniffkit.classifier.ResultClassifier.

Tests cover:
  - classify_file() happy path and failure modes
  - process_results() directory walking, dry-run, and file copying
  - CLI argument validation (via _build_parser)
  - target_types filtering
  - confidence threshold behaviour

Run with:
    pytest tests/test_classifier.py -v
"""

import json
import shutil
from pathlib import Path

import pytest

from sniffkit.classifier import ClassificationResult, ResultClassifier, _build_parser


# =============================================================================
# Helpers — write temp .txt files with known content
# =============================================================================

HTML_CONTENT = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Test</title></head>
<body>
    <div class="container">
        <p>Hello <a href="#">world</a>.</p>
    </div>
    <script src="app.js"></script>
</body>
</html>
"""

CSS_CONTENT = """\
body { margin: 0; padding: 0; }
.container { max-width: 1200px; }
@media (max-width: 768px) { .container { padding: 1rem; } }
h1 { color: #333; font-size: 2rem; }
"""

JSON_CONTENT = json.dumps({
    "experiment_id": "exp_01",
    "model": "gemma4:e2b",
    "status": "complete",
    "runs": [{"id": 1}, {"id": 2}],
})

MD_CONTENT = """\
# Heading One

## Heading Two

- item one
- item two

**bold text** and `inline code`.

```python
print("hello")
```
"""

SQL_CONTENT = """\
SELECT id, model, status FROM runs WHERE experiment_id = 'exp_01' ORDER BY id;
CREATE TABLE results (id SERIAL PRIMARY KEY, value TEXT NOT NULL);
INSERT INTO results (value) VALUES ('test');
"""

PLAIN_CONTENT = """\
This is just plain text with no special syntax.
It should not be classified as anything confidently.
"""


def write_txt(tmp_path: Path, name: str, content: str) -> Path:
    """Write content to a .txt file in tmp_path and return the path."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# =============================================================================
# ClassificationResult dataclass
# =============================================================================

class TestClassificationResult:
    def test_instantiates_with_required_fields(self, tmp_path):
        p = write_txt(tmp_path, "x.txt", "hi")
        r = ClassificationResult(
            source_path=p,
            dest_path=None,
            type_label=None,
            confidence=0.0,
            skipped=True,
            dry_run=True,
        )
        assert r.error is None  # default

    def test_error_field_defaults_none(self, tmp_path):
        p = write_txt(tmp_path, "x.txt", "hi")
        r = ClassificationResult(
            source_path=p,
            dest_path=None,
            type_label=None,
            confidence=0.0,
            skipped=True,
            dry_run=False,
        )
        assert r.error is None


# =============================================================================
# ResultClassifier — constructor
# =============================================================================

class TestResultClassifierInit:
    def test_default_construction(self):
        c = ResultClassifier()
        assert c.min_confidence == 0.6
        assert c.target_types is None
        assert c.verbose is False

    def test_all_detectors_active_by_default(self):
        c = ResultClassifier()
        assert set(c._detectors.keys()) == {"css", "html", "json", "md", "sql"}

    def test_target_types_filters_detectors(self):
        c = ResultClassifier(target_types=["html", "css"])
        assert set(c._detectors.keys()) == {"html", "css"}

    def test_unknown_target_type_raises(self):
        with pytest.raises(ValueError, match="Unknown target type"):
            ResultClassifier(target_types=["html", "notatype"])

    def test_custom_min_confidence(self):
        c = ResultClassifier(min_confidence=0.9)
        assert c.min_confidence == 0.9


# =============================================================================
# ResultClassifier.classify_file()
# =============================================================================

class TestClassifyFile:
    def test_classifies_html_correctly(self, tmp_path):
        p = write_txt(tmp_path, "page.txt", HTML_CONTENT)
        result = ResultClassifier().classify_file(p)
        assert result.type_label == "html"
        assert result.confidence >= 0.6
        assert not result.skipped
        assert result.error is None

    def test_classifies_css_correctly(self, tmp_path):
        p = write_txt(tmp_path, "styles.txt", CSS_CONTENT)
        result = ResultClassifier().classify_file(p)
        assert result.type_label == "css"
        assert result.confidence >= 0.6
        assert not result.skipped

    def test_classifies_json_correctly(self, tmp_path):
        p = write_txt(tmp_path, "data.txt", JSON_CONTENT)
        result = ResultClassifier().classify_file(p)
        assert result.type_label == "json"
        assert result.confidence == 1.0
        assert not result.skipped

    def test_classifies_md_correctly(self, tmp_path):
        p = write_txt(tmp_path, "readme.txt", MD_CONTENT)
        result = ResultClassifier().classify_file(p)
        assert result.type_label == "md"
        assert result.confidence >= 0.6
        assert not result.skipped

    def test_classifies_sql_correctly(self, tmp_path):
        p = write_txt(tmp_path, "schema.txt", SQL_CONTENT)
        result = ResultClassifier().classify_file(p)
        assert result.type_label == "sql"
        assert result.confidence >= 0.6
        assert not result.skipped

    def test_plain_text_is_skipped(self, tmp_path):
        p = write_txt(tmp_path, "note.txt", PLAIN_CONTENT)
        result = ResultClassifier().classify_file(p)
        assert result.skipped
        assert result.type_label is None

    def test_source_path_preserved(self, tmp_path):
        p = write_txt(tmp_path, "page.txt", HTML_CONTENT)
        result = ResultClassifier().classify_file(p)
        assert result.source_path == p

    def test_dest_path_has_correct_extension(self, tmp_path):
        p = write_txt(tmp_path, "page.txt", HTML_CONTENT)
        result = ResultClassifier().classify_file(p)
        assert result.dest_path is not None
        assert result.dest_path.suffix == ".html"
        assert result.dest_path.stem == "page"

    def test_nonexistent_file_returns_error_result(self, tmp_path):
        p = tmp_path / "ghost.txt"
        result = ResultClassifier().classify_file(p)
        assert result.skipped
        assert result.error is not None

    def test_high_threshold_causes_skip(self, tmp_path):
        p = write_txt(tmp_path, "styles.txt", CSS_CONTENT)
        result = ResultClassifier(min_confidence=0.99).classify_file(p)
        # CSS sample is unlikely to hit 0.99
        assert result.skipped

    def test_target_type_filter_skips_other_types(self, tmp_path):
        # Feed HTML to a classifier that only knows CSS — should skip
        p = write_txt(tmp_path, "page.txt", HTML_CONTENT)
        result = ResultClassifier(target_types=["css"]).classify_file(p)
        assert result.skipped

    def test_dry_run_flag_not_set_by_classify_file(self, tmp_path):
        # classify_file() itself doesn't set dry_run — process_results does
        p = write_txt(tmp_path, "page.txt", HTML_CONTENT)
        result = ResultClassifier().classify_file(p)
        assert result.dry_run is False


# =============================================================================
# ResultClassifier.process_results()
# =============================================================================

class TestProcessResults:
    def test_returns_empty_list_when_no_txt_files(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        out_dir = tmp_path / "out"
        classifier = ResultClassifier()
        results = classifier.process_results(results_dir, out_dir, dry_run=True)
        assert results == []

    def test_raises_on_nonexistent_results_dir(self, tmp_path):
        classifier = ResultClassifier()
        with pytest.raises(ValueError, match="does not exist"):
            classifier.process_results(
                tmp_path / "no_such_dir",
                tmp_path / "out",
                dry_run=True,
            )

    def test_dry_run_writes_no_files(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        write_txt(results_dir, "page.txt", HTML_CONTENT)
        out_dir = tmp_path / "out"

        ResultClassifier().process_results(results_dir, out_dir, dry_run=True)

        assert not out_dir.exists(), "dry_run should not create output_dir"

    def test_dry_run_flag_set_on_results(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        write_txt(results_dir, "page.txt", HTML_CONTENT)
        out_dir = tmp_path / "out"

        results = ResultClassifier().process_results(results_dir, out_dir, dry_run=True)
        assert all(r.dry_run for r in results)

    def test_non_dry_run_creates_output_dir(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        write_txt(results_dir, "page.txt", HTML_CONTENT)
        out_dir = tmp_path / "out"

        ResultClassifier().process_results(results_dir, out_dir, dry_run=False)

        assert out_dir.exists()

    def test_non_dry_run_copies_classified_file(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        write_txt(results_dir, "page.txt", HTML_CONTENT)
        out_dir = tmp_path / "out"

        results = ResultClassifier().process_results(results_dir, out_dir, dry_run=False)

        classified = [r for r in results if not r.skipped]
        assert len(classified) == 1
        assert classified[0].dest_path.exists()
        assert classified[0].dest_path.suffix == ".html"

    def test_original_txt_not_deleted(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        original = write_txt(results_dir, "page.txt", HTML_CONTENT)
        out_dir = tmp_path / "out"

        ResultClassifier().process_results(results_dir, out_dir, dry_run=False)

        assert original.exists(), "Original .txt file must not be deleted"

    def test_walks_subdirectories(self, tmp_path):
        results_dir = tmp_path / "results"
        subdir = results_dir / "exp_01"
        subdir.mkdir(parents=True)
        write_txt(subdir, "output.txt", HTML_CONTENT)
        out_dir = tmp_path / "out"

        results = ResultClassifier().process_results(results_dir, out_dir, dry_run=True)
        assert len(results) == 1
        assert results[0].source_path.name == "output.txt"

    def test_skipped_files_included_in_results(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        write_txt(results_dir, "note.txt", PLAIN_CONTENT)
        out_dir = tmp_path / "out"

        results = ResultClassifier().process_results(results_dir, out_dir, dry_run=True)
        assert len(results) == 1
        assert results[0].skipped

    def test_mixed_files_classified_and_skipped(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        write_txt(results_dir, "page.txt",  HTML_CONTENT)
        write_txt(results_dir, "styles.txt", CSS_CONTENT)
        write_txt(results_dir, "note.txt",  PLAIN_CONTENT)
        out_dir = tmp_path / "out"

        results = ResultClassifier().process_results(results_dir, out_dir, dry_run=True)
        classified = [r for r in results if not r.skipped]
        skipped    = [r for r in results if r.skipped]

        assert len(classified) == 2
        assert len(skipped) == 1

    def test_result_count_matches_txt_file_count(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        for i, content in enumerate([HTML_CONTENT, CSS_CONTENT, JSON_CONTENT]):
            write_txt(results_dir, f"file_{i}.txt", content)
        out_dir = tmp_path / "out"

        results = ResultClassifier().process_results(results_dir, out_dir, dry_run=True)
        assert len(results) == 3

    def test_dest_path_is_full_path_not_just_filename(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        write_txt(results_dir, "page.txt", HTML_CONTENT)
        out_dir = tmp_path / "out"

        results = ResultClassifier().process_results(results_dir, out_dir, dry_run=True)
        classified = [r for r in results if not r.skipped]
        assert len(classified) == 1
        assert classified[0].dest_path.parent == out_dir


# =============================================================================
# CLI parser
# =============================================================================

class TestCLIParser:
    def setup_method(self):
        self.parser = _build_parser()

    def test_default_results_dir_is_cwd(self):
        args = self.parser.parse_args([])
        assert args.results_dir == Path(".")

    def test_dry_run_flag(self):
        args = self.parser.parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_dry_run_default_false(self):
        args = self.parser.parse_args([])
        assert args.dry_run is False

    def test_verbose_flag(self):
        args = self.parser.parse_args(["--verbose"])
        assert args.verbose is True

    def test_list_detectors_flag(self):
        args = self.parser.parse_args(["--list-detectors"])
        assert args.list_detectors is True

    def test_min_confidence_parsed(self):
        args = self.parser.parse_args(["--min-confidence", "0.75"])
        assert args.min_confidence == pytest.approx(0.75)

    def test_target_types_parsed(self):
        args = self.parser.parse_args(["--target-types", "html", "css"])
        assert args.target_types == ["html", "css"]

    def test_output_dir_parsed(self):
        args = self.parser.parse_args(["--output-dir", "/tmp/out"])
        assert args.output_dir == Path("/tmp/out")

    def test_results_dir_parsed(self):
        args = self.parser.parse_args(["--results-dir", "/tmp/results"])
        assert args.results_dir == Path("/tmp/results")
