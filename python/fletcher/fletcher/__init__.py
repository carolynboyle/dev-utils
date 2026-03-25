"""
fletcher - GitHub URL manifest generator

Part of the dev-utils toolkit / Project Crew.
Generates .fletch manifests mapping project files to GitHub URLs.

Public API:
    build_url_manifest(paths, repo, branch, url_type) -> dict
    write_manifest(manifest, output_path) -> None
    main() -> None  (CLI entry point)
"""

from fletcher.fletcher import build_url_manifest, write_manifest, main

__version__ = "0.1.0"
__author__ = "Carolyn Boyle"
__description__ = "GitHub URL manifest generator for dev-utils / Project Crew"

__all__ = ["build_url_manifest", "write_manifest", "main"]
