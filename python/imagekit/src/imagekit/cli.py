
"""imagekit CLI entry point."""

import argparse
import sys
from pathlib import Path

from imagekit.encode import ImageEncoder


def cmd_encode(args: argparse.Namespace) -> int:
    """Handle the encode subcommand."""
    encoder = ImageEncoder()
    try:
        result = encoder.encode(args.image, output_format=args.format)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(result, encoding="utf-8")
        print(f"Written to {out_path}")
    else:
        print(result)

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="imagekit",
        description="Image utility toolkit"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # encode subcommand
    enc = subparsers.add_parser("encode", help="Encode an image to base64")
    enc.add_argument("image", help="Path to the image file")
    enc.add_argument(
        "-o", "--output",
        help="Write output to this file instead of stdout",
        default=None
    )
    enc.add_argument(
        "--format",
        choices=["data_uri", "raw"],
        default=None,
        help="Output format: data_uri (default) or raw base64"
    )
    enc.set_defaults(func=cmd_encode)

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))
