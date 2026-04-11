# builtins.py

**Path:** python/mcpkit/src/mcpkit/handlers/builtins.py
**Syntax:** python
**Generated:** 2026-04-06 08:55:14

```python
"""
mcpkit.handlers.builtins - Built-in handler functions.

Common operations that most workflows need:
- Read/write files
- Read YAML/JSON
- Fetch remote content
- List files
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import requests
import yaml

from mcpkit.exceptions import ExecutionError
from mcpkit.utils import expand_path


# -- File I/O -----------------------------------------------------------------


def read_file(path: str) -> str:
    """
    Read text file content.

    Args:
        path: File path (supports ~ expansion)

    Returns:
        File content as string

    Raises:
        ExecutionError: If file not found or unreadable
    """
    try:
        file_path = expand_path(path)
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ExecutionError(f"File not found: {path}")
    except Exception as e:
        raise ExecutionError(f"Could not read file {path}: {e}")


def write_file(path: str, content: str, overwrite: bool = True) -> bool:
    """
    Write content to a file.

    Args:
        path: File path (supports ~ expansion)
        content: Content to write
        overwrite: If False, raise error if file exists

    Returns:
        True on success

    Raises:
        ExecutionError: If write fails
    """
    try:
        file_path = expand_path(path)

        if file_path.exists() and not overwrite:
            raise ExecutionError(f"File already exists: {path}")

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return True
    except ExecutionError:
        raise
    except Exception as e:
        raise ExecutionError(f"Could not write to {path}: {e}")


def read_yaml(file_path: str) -> Dict[str, Any]:
    """
    Read and parse a YAML file.

    Args:
        file_path: Path to YAML file

    Returns:
        Parsed YAML as dict

    Raises:
        ExecutionError: If file not found or invalid YAML
    """
    try:
        path = expand_path(file_path)
        if not path.exists():
            raise ExecutionError(f"File not found: {file_path}")

        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        if data is None:
            return {}

        return data
    except ExecutionError:
        raise
    except yaml.YAMLError as e:
        raise ExecutionError(f"Invalid YAML in {file_path}: {e}")
    except Exception as e:
        raise ExecutionError(f"Could not read YAML from {file_path}: {e}")


def read_json(file_path: str) -> Dict[str, Any]:
    """
    Read and parse a JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON as dict

    Raises:
        ExecutionError: If file not found or invalid JSON
    """
    try:
        path = expand_path(file_path)
        if not path.exists():
            raise ExecutionError(f"File not found: {file_path}")

        content = path.read_text(encoding="utf-8")
        return json.loads(content)
    except ExecutionError:
        raise
    except json.JSONDecodeError as e:
        raise ExecutionError(f"Invalid JSON in {file_path}: {e}")
    except Exception as e:
        raise ExecutionError(f"Could not read JSON from {file_path}: {e}")


def write_json(file_path: str, data: Dict[str, Any], pretty: bool = True) -> bool:
    """
    Write data to a JSON file.

    Args:
        file_path: Path to JSON file
        data: Data to write
        pretty: If True, pretty-print the JSON

    Returns:
        True on success

    Raises:
        ExecutionError: If write fails
    """
    try:
        path = expand_path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if pretty:
            content = json.dumps(data, indent=2)
        else:
            content = json.dumps(data)

        path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        raise ExecutionError(f"Could not write JSON to {file_path}: {e}")


# -- Remote Content -----------------------------------------------------------


def fetch_url(url: str, timeout: int = 30) -> str:
    """
    Fetch raw content from a URL.

    Args:
        url: Full URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Raw response content as string

    Raises:
        ExecutionError: If fetch fails
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise ExecutionError(f"Could not fetch {url}: {e}")
    except Exception as e:
        raise ExecutionError(f"Unexpected error fetching {url}: {e}")


# -- Listing and Inspection ---------------------------------------------------


def list_files(directory: str, pattern: str = "*") -> List[str]:
    """
    List files in a directory.

    Args:
        directory: Directory path (supports ~ expansion)
        pattern: Glob pattern (e.g., "*.md", "src/**/*.py")

    Returns:
        List of file paths relative to directory

    Raises:
        ExecutionError: If directory not found
    """
    try:
        dir_path = expand_path(directory)

        if not dir_path.exists():
            raise ExecutionError(f"Directory not found: {directory}")

        if not dir_path.is_dir():
            raise ExecutionError(f"Not a directory: {directory}")

        # Use glob to find matching files
        matching = list(dir_path.glob(pattern))

        # Return relative paths
        return [str(m.relative_to(dir_path)) for m in matching if m.is_file()]
    except ExecutionError:
        raise
    except Exception as e:
        raise ExecutionError(f"Could not list files in {directory}: {e}")


def file_exists(path: str) -> bool:
    """
    Check if a file exists.

    Args:
        path: File path (supports ~ expansion)

    Returns:
        True if file exists, False otherwise
    """
    try:
        file_path = expand_path(path)
        return file_path.exists()
    except Exception:
        return False

```
