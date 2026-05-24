# sniffkit

*"for when you need to know what's in the bag"*

Content-type detector and file classifier for raw text output. Reads `.txt`
files, detects their content type by heuristic analysis, and copies them to
a target directory with the correct file extension. Files that cannot be
classified with sufficient confidence are skipped and reported.

Part of the [dev-utils](https://github.com/carolynboyle/dev-utils) ecosystem.

---

## The Problem

LLM output files are often written as `.txt` regardless of their actual
content. A file containing a complete HTML page, a CSS stylesheet, or a SQL
migration is still named `run_042.txt`. sniffkit makes them usable without
manual inspection.

Primary consumer: [designing-gemma](https://github.com/carolynboyle/designing-gemma),
where experiment output files need to be classified before they can be served
as web pages or imported into a database.

---

## Installation

```bash
pip install -e ~/projects/dev-utils/python/sniffkit
```

No third-party dependencies. All detection uses stdlib only (`re`, `json`,
`pathlib`). Requires Python 3.11+.

---

## CLI Usage

```
sniffkit [--results-dir PATH] [--output-dir PATH] [--target-types TYPE ...]
         [--dry-run] [--min-confidence FLOAT] [--verbose] [--list-detectors]
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--results-dir PATH` | `.` | Root directory to walk for `.txt` files |
| `--output-dir PATH` | *(required unless --dry-run)* | Where to copy classified files |
| `--target-types TYPE ...` | all | One or more type labels: `html css json md sql` |
| `--dry-run` | off | Compute and display results without writing any files |
| `--min-confidence FLOAT` | `0.6` | Minimum confidence score to accept (0.0–1.0) |
| `--verbose` | off | Show per-file detector scores |
| `--list-detectors` | — | Print all registered detectors and exit |

### Examples

```bash
# See what would be classified without writing anything
sniffkit --results-dir experiments/09_website/results --dry-run --verbose

# Classify all types, copy to classified/
sniffkit \
  --results-dir experiments/09_website/results \
  --output-dir experiments/09_website/classified

# Classify only HTML and CSS
sniffkit \
  --results-dir experiments/08_ui/results \
  --output-dir experiments/08_ui/classified \
  --target-types html css

# See what detectors are registered
sniffkit --list-detectors
```

### Output format

```
sniffkit — scanning experiments/09_website/results for [all]

  run_081_gemma4-e2b_add_navbar_gear.txt  →  html  (0.94)  →  run_081_gemma4-e2b_add_navbar_gear.html
  run_082_gemma4-e4b_add_navbar_gear.txt  →  html  (0.91)  →  run_082_gemma4-e4b_add_navbar_gear.html
  run_083_gemma4-e2b_settings_page.txt    →  html  (0.88)  →  run_083_gemma4-e2b_settings_page.html
  run_084_gemma4-e4b_settings_page.txt    →  ?     (0.41)  →  skipped (below threshold)

Summary: 3 classified, 1 skipped, 0 errors
Destination: experiments/09_website/classified
```

Verbose mode adds a score block per file showing every detector's result
before the winner is selected.

---

## Running Against Multiple Directories

sniffkit processes one `--results-dir` at a time. For projects with multiple
source directories (e.g. one per experiment), use a wrapper script to loop:

```bash
for exp in experiments/*/; do
    results="${exp}results"
    classified="${exp}classified"
    if [[ -d "$results" ]]; then
        sniffkit --results-dir "$results" --output-dir "$classified"
    fi
done
```

Safe to re-run — existing classified files are overwritten, nothing is deleted.

### Planned: `--parent-dir` flag

A future `--parent-dir` flag will handle this pattern natively:

```bash
sniffkit --parent-dir experiments/ --source-dir results --output-dir classified
```

This will walk `experiments/*/results/` and write to `experiments/*/classified/`
without a wrapper script. The flag names are generic — no assumptions about
what the parent directory contains or what the subdirectories are called.

---

## Detectors

| Label | Extension | Detection method |
|---|---|---|
| `html` | `.html` | Tag density, DOCTYPE, structural HTML patterns |
| `css` | `.css` | Selector/property pattern density |
| `json` | `.json` | Attempts `json.loads()` first (score 1.0 on success), then structural heuristics |
| `md` | `.md` | Heading, list, and fenced code block pattern density |
| `sql` | `.sql` | Keyword and clause pattern density |

Each detector returns a confidence score between 0.0 and 1.0. The highest
scoring detector above `--min-confidence` wins. Files where no detector
clears the threshold are skipped.

---

## Python API

```python
from pathlib import Path
from sniffkit.classifier import ResultClassifier

classifier = ResultClassifier(
    min_confidence=0.6,
    target_types=None,   # None = all types
    verbose=False,
)

results = classifier.process_results(
    results_dir=Path("experiments/09_website/results"),
    output_dir=Path("experiments/09_website/classified"),
    dry_run=False,
)

for r in results:
    if not r.skipped:
        print(f"  {r.source_path.name} → {r.type_label} → {r.dest_path.name}")
    else:
        print(f"  {r.source_path.name} → skipped")
```

### Adding a detector

1. Create `src/sniffkit/detectors/mytype_detector.py`
2. Decorate the class with `@register`
3. Add the import to `src/sniffkit/detectors/__init__.py`

```python
from sniffkit.detectors import register

@register
class MyTypeDetector:
    type_label = "mytype"
    extension  = ".mytype"

    def detect(self, text: str) -> float:
        # Return 0.0–1.0
        ...
```

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Completed — even if some files were skipped or had errors |
| `1` | Fatal error before processing began (bad args, unreadable directory) |

---

## Part of Project Crew

sniffkit is one tool in the dev-utils / Project Crew ecosystem:

- **doc-gen** — filesystem manifest generator
- **fletcher** — GitHub URL manifest generator
- **treekit** — directory tree scaffolding from markdown
- **dbkit** — PostgreSQL/SQLite abstraction layer
- **viewkit** — YAML-driven SQL query and view builder
- **sniffkit** — content-type detector and file classifier ← this

---

## Author

Carolyn Boyle — MIT License
