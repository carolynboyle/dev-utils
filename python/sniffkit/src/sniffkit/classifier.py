"""
sniffkit.classifier
~~~~~~~~~~~~~~~~~~~
ResultClassifier — walks a directory tree, classifies .txt files by
content type, and copies them to a target directory with the correct
file extension.

CLI entry point: sniffkit
"""

import argparse
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sniffkit.detectors import get_registry


# =============================================================================
# Result dataclass
# =============================================================================

@dataclass
class ClassificationResult:
    """Result of classifying a single file."""
    source_path:  Path
    dest_path:    Path | None
    type_label:   str | None
    confidence:   float
    skipped:      bool
    dry_run:      bool
    error:        str | None = field(default=None)


# =============================================================================
# Classifier
# =============================================================================

class ResultClassifier:
    """
    Walks a directory tree, classifies .txt files by content type,
    and copies them to a target directory with the correct extension.

    Original .txt files are never modified or deleted.
    """

    def __init__(
        self,
        min_confidence: float = 0.6,
        target_types: list[str] | None = None,
        verbose: bool = False,
    ):
        """
        Args:
            min_confidence: Minimum score to accept a classification.
            target_types:   If provided, only run detectors for these
                            type labels. All others are skipped entirely.
            verbose:        If True, emit per-file detector scores to stdout.
        """
        self.min_confidence = min_confidence
        self.target_types   = target_types
        self.verbose        = verbose

        # Build active detector set from registry
        registry = get_registry()
        if target_types is not None:
            unknown = set(target_types) - set(registry)
            if unknown:
                raise ValueError(
                    f"Unknown target type(s): {', '.join(sorted(unknown))}. "
                    f"Registered: {', '.join(sorted(registry))}"
                )
            self._detectors = {
                label: cls for label, cls in registry.items()
                if label in target_types
            }
        else:
            self._detectors = dict(registry)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def classify_file(self, path: Path) -> ClassificationResult:
        """
        Classify a single file.

        Runs only the active detectors (filtered by target_types).
        Returns the highest-confidence result above min_confidence,
        or a skipped result if none qualify.

        Never raises — errors are captured in result.error.

        Args:
            path: Path to a .txt file.

        Returns:
            ClassificationResult
        """
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:  # pylint: disable=broad-except
            return ClassificationResult(
                source_path=path,
                dest_path=None,
                type_label=None,
                confidence=0.0,
                skipped=True,
                dry_run=False,
                error=str(exc),
            )

        scores: dict[str, float] = {}
        for label, detector_cls in self._detectors.items():
            try:
                score = detector_cls().detect(text)
            except Exception as exc:  # pylint: disable=broad-except
                score = 0.0
                if self.verbose:
                    print(f"    [{label}] ERROR: {exc}")
            scores[label] = score
            if self.verbose:
                print(f"    [{label}] {score:.2f}")

        # Find the winner — highest score above threshold
        winner_label    = None
        winner_score    = 0.0
        winner_ext      = None
        for label, score in scores.items():
            if score >= self.min_confidence and score > winner_score:
                winner_label = label
                winner_score = score
                winner_ext   = self._detectors[label].extension

        if winner_label is None:
            return ClassificationResult(
                source_path=path,
                dest_path=None,
                type_label=None,
                confidence=winner_score,
                skipped=True,
                dry_run=False,
            )

        dest_name = path.stem + winner_ext
        return ClassificationResult(
            source_path=path,
            dest_path=Path(dest_name),   # resolved to full path in process_results
            type_label=winner_label,
            confidence=winner_score,
            skipped=False,
            dry_run=False,
        )

    def process_results(
        self,
        results_dir: Path,
        output_dir:  Path,
        dry_run:     bool = True,
    ) -> list[ClassificationResult]:
        """
        Walk results_dir recursively, classify every .txt file found,
        and copy classified files to output_dir.

        Original .txt files are never modified or deleted.
        output_dir is created if it does not exist (unless dry_run).

        Args:
            results_dir: Root directory to walk.
            output_dir:  Destination for classified files.
            dry_run:     If True, compute results but write nothing.

        Returns:
            List of ClassificationResult for every .txt file encountered.
        """
        if not results_dir.exists():
            raise ValueError(f"results_dir does not exist: {results_dir}")

        txt_files = sorted(results_dir.rglob("*.txt"))
        if not txt_files:
            return []

        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)

        results: list[ClassificationResult] = []

        for txt_path in txt_files:
            if self.verbose:
                print(f"\n  {txt_path.name}")

            result = self.classify_file(txt_path)
            result.dry_run = dry_run

            if not result.skipped and result.dest_path is not None:
                full_dest = output_dir / result.dest_path.name
                result.dest_path = full_dest
                if not dry_run:
                    try:
                        shutil.copy2(txt_path, full_dest)
                    except Exception as exc:  # pylint: disable=broad-except
                        result.error   = str(exc)
                        result.skipped = True

            results.append(result)

        return results


# =============================================================================
# CLI
# =============================================================================

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sniffkit",
        description="Classify .txt files by content type and copy with correct extension.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("."),
        metavar="PATH",
        help="Root directory to walk for .txt files (default: current directory)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help="Where to copy classified files (required unless --dry-run)",
    )
    parser.add_argument(
        "--target-types",
        nargs="+",
        metavar="TYPE",
        default=None,
        help="One or more type labels to detect (default: all). e.g. --target-types html css",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and display results without writing any files",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.6,
        metavar="FLOAT",
        help="Minimum confidence score to accept, 0.0-1.0 (default: 0.6)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show per-file detector scores",
    )
    parser.add_argument(
        "--list-detectors",
        action="store_true",
        help="Print all registered detector labels and extensions, then exit",
    )
    return parser


def main() -> None:
    """CLI entry point."""
    parser = _build_parser()
    args   = parser.parse_args()

    # --list-detectors
    if args.list_detectors:
        from sniffkit.detectors import get_registry  # pylint: disable=import-outside-toplevel
        registry = get_registry()
        print("Registered detectors:")
        for label, cls in sorted(registry.items()):
            print(f"  {label:<10} {cls.extension}")
        sys.exit(0)

    # Validate args
    if not args.dry_run and args.output_dir is None:
        parser.error("--output-dir is required unless --dry-run is set")

    if args.min_confidence < 0.0 or args.min_confidence > 1.0:
        parser.error("--min-confidence must be between 0.0 and 1.0")

    # Build classifier
    try:
        classifier = ResultClassifier(
            min_confidence=args.min_confidence,
            target_types=args.target_types,
            verbose=args.verbose,
        )
    except ValueError as exc:
        parser.error(str(exc))

    # Header
    type_display = ", ".join(args.target_types) if args.target_types else "all"
    print(f"\nsniffkit — scanning {args.results_dir} for [{type_display}]")
    if args.dry_run:
        print("(dry run — no files will be written)\n")
    else:
        print()

    # Run
    try:
        results = classifier.process_results(
            results_dir=args.results_dir,
            output_dir=args.output_dir or Path("."),
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # Output
    classified = 0
    skipped    = 0
    errors     = 0

    for r in results:
        if r.error:
            print(f"  {r.source_path.name:<60}  ERROR: {r.error}")
            errors += 1
        elif r.skipped:
            top_score = f"({r.confidence:.2f})" if r.confidence > 0 else "(0.00)"
            print(f"  {r.source_path.name:<60}  ?    {top_score:<8}  skipped")
            skipped += 1
        else:
            dest_name = r.dest_path.name if r.dest_path else "?"
            prefix    = "[dry run] " if r.dry_run else ""
            print(
                f"  {r.source_path.name:<60}  "
                f"{r.type_label:<6} ({r.confidence:.2f})  →  "
                f"{prefix}{dest_name}"
            )
            classified += 1

    # Summary
    print(f"\nSummary: {classified} classified, {skipped} skipped, {errors} errors")
    if not args.dry_run and args.output_dir:
        print(f"Destination: {args.output_dir}")

    sys.exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    main()
