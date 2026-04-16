# executor.py

**Path:** python/mcpkit/src/mcpkit/executor.py
**Syntax:** python
**Generated:** 2026-04-16 10:47:57

```python
"""
mcpkit.executor - Handler execution and validation.

Calls handler functions with input parameters, validates inputs against
tool schemas, and wraps errors clearly.
"""

from typing import Any, Dict, Optional

from mcpkit.exceptions import ExecutionError, ValidationError
from mcpkit.tool_registry import ToolRegistry


class Executor:
    """
    Execute MCP tool handlers.

    Validates inputs, calls handler functions, catches errors, and
    returns results.
    """

    def __init__(self, tool_registry: ToolRegistry):
        """
        Initialize executor.

        Args:
            tool_registry: ToolRegistry instance with loaded tools
        """
        self.registry = tool_registry

    def execute(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool handler.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Input parameters for the handler

        Returns:
            Handler output

        Raises:
            ValidationError: If input validation fails
            ExecutionError: If handler execution fails
        """
        # Get the tool
        tool = self.registry.get_tool(tool_name)

        # Validate inputs
        self._validate_inputs(tool_name, tool.input_schema, kwargs)

        # Execute handler
        try:
            result = tool.handler_func(**kwargs)
            return result
        except ExecutionError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            raise ExecutionError(
                f"Handler '{tool_name}' failed: {e}\n"
                f"Handler: {tool.handler_ref}\n"
                f"Input: {kwargs}"
            ) from e

    def _validate_inputs(
        self, tool_name: str, schema: Dict[str, Any], inputs: Dict[str, Any]
    ) -> None:
        """
        Validate input parameters against tool schema.

        Simple validation:
        - Check that all required fields are present
        - Check that provided fields are of expected type (loose check)

        Args:
            tool_name: Tool name (for error messages)
            schema: Input schema from tool definition
            inputs: Actual input parameters

        Raises:
            ValidationError: If validation fails
        """
        if not schema:
            # No schema defined, skip validation
            return

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Check required fields
        missing = [f for f in required if f not in inputs]
        if missing:
            raise ValidationError(
                f"Tool '{tool_name}' missing required inputs: {', '.join(missing)}"
            )

        # Check for unexpected fields (warn, don't error)
        unexpected = [f for f in inputs.keys() if f not in properties.keys()]
        if unexpected:
            # Just log, don't fail — handler might accept extra kwargs
            pass

        # Type checking (loose — just check if type matches reasonably)
        for field, value in inputs.items():
            if field not in properties:
                continue

            prop_def = properties[field]
            expected_type = prop_def.get("type")

            if expected_type and not self._type_matches(value, expected_type):
                raise ValidationError(
                    f"Tool '{tool_name}' field '{field}' should be {expected_type}, "
                    f"got {type(value).__name__}"
                )

    @staticmethod
    def _type_matches(value: Any, expected_type: str) -> bool:
        """
        Check if a value matches an expected JSON Schema type.

        Args:
            value: The actual value
            expected_type: JSON Schema type (string, number, integer, boolean, object, array, etc.)

        Returns:
            True if type matches, False otherwise
        """
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "object": dict,
            "array": list,
            "null": type(None),
        }

        if expected_type not in type_map:
            # Unknown type, don't validate
            return True

        expected_python_type = type_map[expected_type]
        return isinstance(value, expected_python_type)

```
