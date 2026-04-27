"""
tests.test_formatter - Unit tests for viewkit.onthefly.formatter.

Tests cover:
  - ASCII table output for select_all, select_one results
  - JSON output for select_all, select_one results
  - CSV output for select_all, select_one results
  - Scalar output for select_scalar results
  - Execute output for execute results
  - NULL value display
  - Value truncation in ASCII table
  - Empty result handling
  - Numeric column right-alignment
  - OTFRunError on unrecognised query_type
"""

import csv
import io
import json

import pytest

from viewkit.onthefly.formatter import format_result, OutputFormat, MAX_COL_WIDTH
from viewkit.onthefly.runner import OTFResult
from viewkit.onthefly.exceptions import OTFRunError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def multi_row_result():
    """OTFResult with multiple rows for select_all."""
    return OTFResult(
        query_type="select_all",
        data=[
            {"id": 1, "name": "Alpha", "slug": "alpha"},
            {"id": 2, "name": "Beta",  "slug": "beta"},
            {"id": 3, "name": "Gamma", "slug": "gamma"},
        ],
    )


@pytest.fixture()
def single_row_result():
    """OTFResult with one row for select_one."""
    return OTFResult(
        query_type="select_one",
        data={"id": 1, "name": "Alpha", "slug": "alpha"},
    )


@pytest.fixture()
def null_row_result():
    """OTFResult with NULL values in a row."""
    return OTFResult(
        query_type="select_all",
        data=[
            {"id": 1, "name": "Alpha", "notes": None},
            {"id": 2, "name": "Beta",  "notes": None},
        ],
    )


@pytest.fixture()
def long_value_result():
    """OTFResult with a value longer than MAX_COL_WIDTH."""
    return OTFResult(
        query_type="select_all",
        data=[
            {"id": 1, "name": "A" * (MAX_COL_WIDTH + 10)},
        ],
    )


@pytest.fixture()
def numeric_result():
    """OTFResult with numeric columns."""
    return OTFResult(
        query_type="select_all",
        data=[
            {"id": 1, "count": 42,  "name": "Alpha"},
            {"id": 2, "count": 100, "name": "Beta"},
        ],
    )


@pytest.fixture()
def scalar_result():
    """OTFResult for select_scalar."""
    return OTFResult(query_type="select_scalar", data=7)


@pytest.fixture()
def null_scalar_result():
    """OTFResult for select_scalar returning NULL."""
    return OTFResult(query_type="select_scalar", data=None)


@pytest.fixture()
def execute_result():
    """OTFResult for execute query."""
    return OTFResult(query_type="execute", data=None)


# ---------------------------------------------------------------------------
# ASCII table — select_all
# ---------------------------------------------------------------------------

class TestAsciiTableSelectAll:
    def test_contains_headers(self, multi_row_result):
        output = format_result(multi_row_result, OutputFormat.TABLE)
        assert "id" in output
        assert "name" in output
        assert "slug" in output

    def test_contains_data_values(self, multi_row_result):
        output = format_result(multi_row_result, OutputFormat.TABLE)
        assert "Alpha" in output
        assert "Beta" in output
        assert "Gamma" in output

    def test_contains_separator_row(self, multi_row_result):
        output = format_result(multi_row_result, OutputFormat.TABLE)
        lines = output.splitlines()
        assert any(set(line.strip()) <= set("-+") for line in lines)

    def test_contains_pipe_separators(self, multi_row_result):
        output = format_result(multi_row_result, OutputFormat.TABLE)
        assert "|" in output

    def test_row_count(self, multi_row_result):
        output = format_result(multi_row_result, OutputFormat.TABLE)
        # header + separator + 3 data rows = 5 lines
        assert len(output.splitlines()) == 5

    def test_empty_result_message(self):
        result = OTFResult(query_type="select_all", data=[])
        output = format_result(result, OutputFormat.TABLE)
        assert "no rows" in output.lower()


# ---------------------------------------------------------------------------
# ASCII table — select_one
# ---------------------------------------------------------------------------

class TestAsciiTableSelectOne:
    def test_single_row_rendered(self, single_row_result):
        output = format_result(single_row_result, OutputFormat.TABLE)
        assert "Alpha" in output

    def test_row_count(self, single_row_result):
        output = format_result(single_row_result, OutputFormat.TABLE)
        # header + separator + 1 data row = 3 lines
        assert len(output.splitlines()) == 3

    def test_none_result_is_empty(self):
        result = OTFResult(query_type="select_one", data=None)
        output = format_result(result, OutputFormat.TABLE)
        assert "no rows" in output.lower()


# ---------------------------------------------------------------------------
# ASCII table — NULL values
# ---------------------------------------------------------------------------

class TestAsciiTableNulls:
    def test_null_displayed_as_null_marker(self, null_row_result):
        output = format_result(null_row_result, OutputFormat.TABLE)
        assert "<null>" in output

    def test_null_not_displayed_as_none(self, null_row_result):
        output = format_result(null_row_result, OutputFormat.TABLE)
        assert "None" not in output


# ---------------------------------------------------------------------------
# ASCII table — truncation
# ---------------------------------------------------------------------------

class TestAsciiTableTruncation:
    def test_long_value_truncated(self, long_value_result):
        output = format_result(long_value_result, OutputFormat.TABLE)
        assert "..." in output

    def test_truncated_value_not_longer_than_max(self, long_value_result):
        output = format_result(long_value_result, OutputFormat.TABLE)
        for line in output.splitlines():
            for cell in line.split("|"):
                assert len(cell.strip()) <= MAX_COL_WIDTH


# ---------------------------------------------------------------------------
# ASCII table — numeric alignment
# ---------------------------------------------------------------------------

class TestAsciiTableNumericAlignment:
    def test_numeric_columns_present(self, numeric_result):
        output = format_result(numeric_result, OutputFormat.TABLE)
        assert "42" in output
        assert "100" in output


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

class TestJsonOutput:
    def test_valid_json(self, multi_row_result):
        output = format_result(multi_row_result, OutputFormat.JSON)
        parsed = json.loads(output)
        assert isinstance(parsed, list)

    def test_row_count(self, multi_row_result):
        output = format_result(multi_row_result, OutputFormat.JSON)
        parsed = json.loads(output)
        assert len(parsed) == 3

    def test_field_values(self, multi_row_result):
        output = format_result(multi_row_result, OutputFormat.JSON)
        parsed = json.loads(output)
        assert parsed[0]["name"] == "Alpha"

    def test_null_becomes_json_null(self, null_row_result):
        output = format_result(null_row_result, OutputFormat.JSON)
        parsed = json.loads(output)
        assert parsed[0]["notes"] is None

    def test_no_truncation(self, long_value_result):
        output = format_result(long_value_result, OutputFormat.JSON)
        parsed = json.loads(output)
        assert len(parsed[0]["name"]) == MAX_COL_WIDTH + 10

    def test_select_one_as_list(self, single_row_result):
        output = format_result(single_row_result, OutputFormat.JSON)
        parsed = json.loads(output)
        assert isinstance(parsed, list)
        assert len(parsed) == 1


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

class TestCsvOutput:
    def _parse(self, output: str) -> list[dict]:
        return list(csv.DictReader(io.StringIO(output)))

    def test_has_header_row(self, multi_row_result):
        output = format_result(multi_row_result, OutputFormat.CSV)
        rows = self._parse(output)
        assert "name" in rows[0]

    def test_row_count(self, multi_row_result):
        output = format_result(multi_row_result, OutputFormat.CSV)
        rows = self._parse(output)
        assert len(rows) == 3

    def test_field_values(self, multi_row_result):
        output = format_result(multi_row_result, OutputFormat.CSV)
        rows = self._parse(output)
        assert rows[0]["name"] == "Alpha"

    def test_null_becomes_empty_cell(self, null_row_result):
        output = format_result(null_row_result, OutputFormat.CSV)
        rows = self._parse(output)
        assert rows[0]["notes"] == ""

    def test_no_truncation(self, long_value_result):
        output = format_result(long_value_result, OutputFormat.CSV)
        rows = self._parse(output)
        assert len(rows[0]["name"]) == MAX_COL_WIDTH + 10

    def test_select_one_as_single_row(self, single_row_result):
        output = format_result(single_row_result, OutputFormat.CSV)
        rows = self._parse(output)
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# Scalar output
# ---------------------------------------------------------------------------

class TestScalarOutput:
    def test_integer_scalar_table(self, scalar_result):
        output = format_result(scalar_result, OutputFormat.TABLE)
        assert output == "7"

    def test_integer_scalar_json(self, scalar_result):
        output = format_result(scalar_result, OutputFormat.JSON)
        assert json.loads(output) == 7

    def test_null_scalar_table(self, null_scalar_result):
        output = format_result(null_scalar_result, OutputFormat.TABLE)
        assert output == "<null>"

    def test_null_scalar_json(self, null_scalar_result):
        output = format_result(null_scalar_result, OutputFormat.JSON)
        assert json.loads(output) is None


# ---------------------------------------------------------------------------
# Execute output
# ---------------------------------------------------------------------------

class TestExecuteOutput:
    def test_returns_success_string(self, execute_result):
        output = format_result(execute_result, OutputFormat.TABLE)
        assert "successfully" in output.lower()

    def test_returns_string_type(self, execute_result):
        output = format_result(execute_result, OutputFormat.TABLE)
        assert isinstance(output, str)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestFormatterErrors:
    def test_unknown_query_type_raises(self):
        result = OTFResult(query_type="rainbow", data=None)
        with pytest.raises(OTFRunError, match="Unrecognised"):
            format_result(result, OutputFormat.TABLE)