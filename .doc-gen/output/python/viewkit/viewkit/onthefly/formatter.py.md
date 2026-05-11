# formatter.py

**Path:** python/viewkit/viewkit/onthefly/formatter.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
viewkit.onthefly.formatter - Output formatting for the OTF query tool.

Formats OTFResult objects as ASCII table, JSON, or CSV strings.
Returns strings only — writing to stdout or file is the caller's concern.

ASCII table output truncates long values to MAX_COL_WIDTH characters.
JSON and CSV output never truncate — full values are always written.

Usage:
    from viewkit.onthefly.formatter import format_result, OutputFormat

    output = format_result(result, OutputFormat.TABLE)
    print(output)
"""

import csv
import io
import json
from enum import Enum
from typing import Any

from viewkit.onthefly.exceptions import OTFRunError
from viewkit.onthefly.runner import OTFResult


# Maximum column width for ASCII table output.
# Values longer than this are truncated with an ellipsis.
# JSON and CSV output is never truncated.
# Override in ~/.config/viewkit/onthefly.yaml (not yet implemented).
MAX_COL_WIDTH = 50

NULL_DISPLAY = "<null>"


class OutputFormat(Enum):
    """Output format options for OTF query results."""

    TABLE = "table"
    JSON  = "json"
    CSV   = "csv"


# -- Execute -----------------------------------------------------------------

def _format_execute(data: Any) -> str:  # pylint: disable=unused-argument
    """
    Format the result of an execute query.

    Args:
        data: Currently None (dbkit.execute returns None).
              After dbkit is updated to return rowcount, data will be
              an int representing rows affected.

    Returns:
        Human-readable status string.
    """
    # After dbkit.execute is updated to return rowcount, replace the
    # return statement below with this block:
    #
    # if data is not None:
    #     return f"Query executed successfully. {data} row(s) affected."
    # return "Query executed successfully. (rows affected: unknown)"

    return "Query executed successfully."


# -- Scalar ------------------------------------------------------------------

def _format_scalar(value: Any, fmt: OutputFormat) -> str:
    """
    Format a scalar result.

    Args:
        value: Single value returned by fetch_scalar(), or None.
        fmt:   Output format.

    Returns:
        Formatted string.
    """
    if fmt == OutputFormat.JSON:
        return json.dumps(value, default=str)
    if value is None:
        return NULL_DISPLAY
    return str(value)


# -- Row normalisation -------------------------------------------------------

def _normalise_rows(result: OTFResult) -> list[dict]:
    """
    Normalise select_all and select_one results to a list of dicts.

    select_all returns list[dict], select_one returns dict | None.
    Both are normalised to list[dict] for uniform formatting.

    Args:
        result: OTFResult with query_type select_all or select_one.

    Returns:
        List of dicts, possibly empty.
    """
    if result.query_type == "select_all":
        return result.data or []
    if result.query_type == "select_one":
        return [result.data] if result.data is not None else []
    return []


# -- Numeric column detection ------------------------------------------------

def _find_numeric_cols(rows: list[dict], headers: list[str]) -> set[str]:
    """
    Identify columns whose values are all numeric (int or float).

    NULL values are ignored when determining column type.

    Args:
        rows:    Raw (unrendered) rows from dbkit.
        headers: Column names to check.

    Returns:
        Set of column names that contain only numeric values.
    """
    numeric_cols = set()
    for col in headers:
        values = [row[col] for row in rows if row[col] is not None]
        if values and all(isinstance(v, (int, float)) for v in values):
            numeric_cols.add(col)
    return numeric_cols


# -- ASCII table -------------------------------------------------------------

def _format_table(rows: list[dict], truncate: bool = True) -> str:
    """
    Format rows as a pipe-separated ASCII table.

    Text values are left-aligned. Numeric values are right-aligned.
    NULL values are displayed as '<null>'.
    Long values are truncated with '...' if truncate is True.

    Args:
        rows:     List of dicts, all with the same keys.
        truncate: If True, truncate values longer than MAX_COL_WIDTH.

    Returns:
        Formatted ASCII table string.
    """
    headers = list(rows[0].keys())

    # Render all values to display strings
    rendered = []
    for row in rows:
        rendered_row = {}
        for col in headers:
            val = row[col]
            rendered_row[col] = NULL_DISPLAY if val is None else str(val)
        rendered.append(rendered_row)

    # Truncate if requested
    if truncate:
        for row in rendered:
            for col in headers:
                if len(row[col]) > MAX_COL_WIDTH:
                    row[col] = row[col][:MAX_COL_WIDTH - 3] + "..."

    # Calculate column widths
    col_widths = {
        col: max(len(col), max(len(row[col]) for row in rendered))
        for col in headers
    }

    # Determine numeric columns for right-alignment
    numeric_cols = _find_numeric_cols(rows, headers)

    # Build output
    lines = []

    # Header row
    header_cells = [col.ljust(col_widths[col]) for col in headers]
    lines.append(" | ".join(header_cells))

    # Separator row
    sep_cells = ["-" * col_widths[col] for col in headers]
    lines.append("-+-".join(sep_cells))

    # Data rows
    for row in rendered:
        cells = []
        for col in headers:
            w = col_widths[col]
            val = row[col]
            cells.append(val.rjust(w) if col in numeric_cols else val.ljust(w))
        lines.append(" | ".join(cells))

    return "\n".join(lines)


# -- JSON --------------------------------------------------------------------

def _format_json(rows: list[dict]) -> str:
    """
    Format rows as a JSON array of objects.

    NULL values become JSON null. Dates and other non-serialisable
    types are converted to strings via default=str.

    Args:
        rows: List of dicts from dbkit (untruncated).

    Returns:
        JSON string.
    """
    return json.dumps(rows, indent=2, default=str)


# -- CSV ---------------------------------------------------------------------

def _format_csv(rows: list[dict]) -> str:
    """
    Format rows as CSV with a header row.

    Uses Python's csv module with excel dialect (standard CSV).
    NULL values become empty cells.
    String quoting only where needed.

    Args:
        rows: List of dicts from dbkit (untruncated).

    Returns:
        CSV string including header row.
    """
    output = io.StringIO()
    headers = list(rows[0].keys())
    writer = csv.DictWriter(
        output,
        fieldnames=headers,
        dialect="excel",
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({
            k: ("" if v is None else v)
            for k, v in row.items()
        })
    return output.getvalue()


# -- Public interface --------------------------------------------------------

def format_result(result: OTFResult, fmt: OutputFormat = OutputFormat.TABLE) -> str:
    """
    Format an OTFResult as a string in the requested output format.

    ASCII table output truncates long values to MAX_COL_WIDTH.
    JSON and CSV output never truncates.

    Args:
        result: OTFResult returned by run_query().
        fmt:    Output format. Defaults to ASCII table.

    Returns:
        Formatted string ready to print or write to a file.

    Raises:
        OTFRunError: If the result type is not recognised.
    """
    if result.query_type == "execute":
        return _format_execute(result.data)

    if result.query_type == "select_scalar":
        return _format_scalar(result.data, fmt)

    if result.query_type in ("select_all", "select_one"):
        rows = _normalise_rows(result)
        if not rows:
            return "(no rows returned)"
        if fmt == OutputFormat.TABLE:
            return _format_table(rows, truncate=True)
        if fmt == OutputFormat.JSON:
            return _format_json(rows)
        if fmt == OutputFormat.CSV:
            return _format_csv(rows)

    raise OTFRunError(
        f"Unrecognised query_type '{result.query_type}' in formatter."
    )

```
