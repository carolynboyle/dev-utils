# workflow.py

**Path:** python/mcpkit/src/mcpkit/workflow.py
**Syntax:** python
**Generated:** 2026-04-11 16:04:24

```python
"""
mcpkit.workflow - Workflow orchestration.

Loads workflow.yaml, executes steps in sequence, handles approval gates,
and manages variable interpolation across steps.

Includes comprehensive logging so workflows can be resumed after interruption.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from mcpkit.exceptions import ConfigError, WorkflowError
from mcpkit.executor import Executor
from mcpkit.tool_registry import ToolRegistry
from mcpkit.utils import expand_path, interpolate


class ExecutionLogEntry:
    """A single entry in the execution log."""

    def __init__(
        self,
        step_num: int,
        name: str,
        tool: str,
        status: str,  # completed, incomplete, failed
        timestamp: str,
        output_variable: Optional[str] = None,
        output_file: Optional[str] = None,
        approval_status: Optional[str] = None,  # approved, denied, pending
        error_message: Optional[str] = None,
    ):
        self.step_num = step_num
        self.name = name
        self.tool = tool
        self.status = status
        self.timestamp = timestamp
        self.output_variable = output_variable
        self.output_file = output_file
        self.approval_status = approval_status
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for YAML serialization."""
        return {
            "step": self.step_num,
            "name": self.name,
            "tool": self.tool,
            "status": self.status,
            "timestamp": self.timestamp,
            "output_variable": self.output_variable,
            "output_file": self.output_file,
            "approval_status": self.approval_status,
            "error_message": self.error_message,
        }


class WorkflowStep:
    """Represents a single step in a workflow."""

    def __init__(self, step_num: int, definition: Dict[str, Any]):
        """
        Initialize a workflow step.

        Args:
            step_num: Step number (1-indexed)
            definition: Step definition from workflow.yaml
        """
        self.step_num = step_num
        self.definition = definition
        self.name = definition.get("name", f"step_{step_num}")
        self.description = definition.get("description", "")
        self.tool = definition.get("tool", "")
        self.args = definition.get("args", {})
        self.approval_required = definition.get("approval_required", False)
        self.approval_message = definition.get("approval_message", "")
        self.save_to_file = definition.get("save_to_file")
        self.save_output_to = definition.get("save_output_to")
        self.on_error = definition.get("on_error", "fail")  # fail, skip, continue

    def __repr__(self) -> str:
        return f"WorkflowStep(step={self.step_num}, name={self.name}, tool={self.tool})"


class Workflow:
    """
    Load and execute a workflow from workflow.yaml.

    Handles step sequencing, variable interpolation, approval gates,
    error handling, and comprehensive execution logging for resumption
    after interruption.
    """

    def __init__(
        self,
        workflow_yaml_path: Path,
        executor: Executor,
        log_file: Optional[Path] = None,
    ):
        """
        Initialize workflow.

        Args:
            workflow_yaml_path: Path to workflow.yaml
            executor: Executor instance for running tools
            log_file: Path to execution log (optional, defaults to workflow_dir/execution.log)

        Raises:
            ConfigError: If workflow.yaml not found or invalid
        """
        self.workflow_yaml_path = expand_path(workflow_yaml_path)
        self.executor = executor
        self.steps: List[WorkflowStep] = []
        self.variables: Dict[str, Any] = {}
        self.results: Dict[int, Any] = {}  # step_num → output
        self.execution_log: List[ExecutionLogEntry] = []

        # Determine log file path
        if log_file:
            self.log_file = expand_path(log_file)
        else:
            self.log_file = self.workflow_yaml_path.parent / "execution.log"

        self._load_workflow()
        self._load_execution_log()

    def _load_workflow(self) -> None:
        """
        Load workflow from YAML file.

        Raises:
            ConfigError: If file not found or invalid YAML
        """
        if not self.workflow_yaml_path.exists():
            raise ConfigError(f"Workflow file not found: {self.workflow_yaml_path}")

        try:
            content = self.workflow_yaml_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            if not data or "workflow" not in data:
                raise ConfigError(
                    f"No 'workflow' section found in {self.workflow_yaml_path}"
                )

            workflow_data = data["workflow"]

            # Load global variables
            self.variables = workflow_data.get("variables", {})

            # Load steps
            steps_data = workflow_data.get("steps", [])
            if not steps_data:
                raise ConfigError(f"No steps defined in {self.workflow_yaml_path}")

            for i, step_def in enumerate(steps_data, 1):
                self.steps.append(WorkflowStep(i, step_def))

        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {self.workflow_yaml_path}: {e}")
        except OSError as e:
            raise ConfigError(f"Could not read {self.workflow_yaml_path}: {e}")

    # ========== NEW: Execution Logging ==========

    def _load_execution_log(self) -> None:
        """
        Load execution log from file if it exists.

        Used to determine which steps have already been completed.
        """
        if not self.log_file.exists():
            self.execution_log = []
            return

        try:
            content = self.log_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            if not data or "execution_log" not in data:
                self.execution_log = []
                return

            log_entries = data["execution_log"]
            self.execution_log = []

            for entry_dict in log_entries:
                entry = ExecutionLogEntry(
                    step_num=entry_dict.get("step"),
                    name=entry_dict.get("name"),
                    tool=entry_dict.get("tool"),
                    status=entry_dict.get("status"),
                    timestamp=entry_dict.get("timestamp"),
                    output_variable=entry_dict.get("output_variable"),
                    output_file=entry_dict.get("output_file"),
                    approval_status=entry_dict.get("approval_status"),
                    error_message=entry_dict.get("error_message"),
                )
                self.execution_log.append(entry)

        except Exception as e:
            print(f"Warning: Could not load execution log: {e}")
            self.execution_log = []

    def _save_execution_log(self) -> None:
        """
        Save execution log to file.

        Called after each step and at workflow completion.
        """
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

            data = {"execution_log": [entry.to_dict() for entry in self.execution_log]}

            self.log_file.write_text(
                yaml.dump(data, default_flow_style=False), encoding="utf-8"
            )
        except Exception as e:
            print(f"Warning: Could not save execution log: {e}")

    def _log_step_completion(
        self,
        step: WorkflowStep,
        status: str,
        output_variable: Optional[str] = None,
        output_file: Optional[str] = None,
        approval_status: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Add an entry to the execution log.

        Args:
            step: The step that was executed
            status: completed, incomplete, or failed
            output_variable: Variable name if output was stored
            output_file: File path if output was saved
            approval_status: approved, denied, or pending
            error_message: Error message if step failed
        """
        entry = ExecutionLogEntry(
            step_num=step.step_num,
            name=step.name,
            tool=step.tool,
            status=status,
            timestamp=datetime.now().isoformat(),
            output_variable=output_variable,
            output_file=output_file,
            approval_status=approval_status,
            error_message=error_message,
        )
        self.execution_log.append(entry)
        self._save_execution_log()

    def _was_step_completed(self, step_num: int) -> bool:
        """
        Check if a step was already completed (from log).

        Args:
            step_num: Step number to check

        Returns:
            True if step completed, False otherwise
        """
        for entry in self.execution_log:
            if entry.step_num == step_num and entry.status == "completed":
                return True
        return False

    def _get_step_log_entry(self, step_num: int) -> Optional[ExecutionLogEntry]:
        """Get the log entry for a step, if it exists."""
        for entry in self.execution_log:
            if entry.step_num == step_num:
                return entry
        return None

    def _build_workflow_context(self) -> str:
        """
        Build a human-readable summary of the complete workflow.

        Used to provide LLM with full context when resuming.

        Returns:
            Formatted workflow description
        """
        lines = []
        lines.append("COMPLETE WORKFLOW DEFINITION:")
        lines.append("=" * 60)

        for step in self.steps:
            lines.append(f"\nStep {step.step_num}: {step.name}")
            if step.description:
                lines.append(f"  Description: {step.description}")
            lines.append(f"  Tool: {step.tool}")
            lines.append(f"  Approval required: {step.approval_required}")
            if step.save_output_to:
                lines.append(f"  Output stored in: {{ {step.save_output_to} }}")

        return "\n".join(lines)

    def _build_execution_summary(self) -> str:
        """
        Build a summary of execution log for LLM context.

        Returns:
            Formatted execution log
        """
        lines = []
        lines.append("EXECUTION LOG (what's been completed):")
        lines.append("=" * 60)

        if not self.execution_log:
            lines.append("(No steps have been executed yet)")
        else:
            for entry in self.execution_log:
                lines.append(f"\nStep {entry.step_num}: {entry.name}")
                lines.append(f"  Status: {entry.status}")
                lines.append(f"  Tool: {entry.tool}")
                lines.append(f"  Timestamp: {entry.timestamp}")
                if entry.approval_status:
                    lines.append(f"  Approval: {entry.approval_status}")
                if entry.output_variable:
                    lines.append(f"  Output variable: {{ {entry.output_variable} }}")
                if entry.output_file:
                    lines.append(f"  Output file: {entry.output_file}")
                if entry.error_message:
                    lines.append(f"  Error: {entry.error_message}")

        return "\n".join(lines)

    def get_llm_context(self) -> str:
        """
        Build complete context for LLM to understand workflow state.

        Used when passing workflow info to the LLM (for step prompts, etc.)

        Returns:
            Formatted context string with workflow and execution log
        """
        workflow = self._build_workflow_context()
        execution = self._build_execution_summary()

        context = f"""{workflow}

{execution}

INSTRUCTIONS FOR LLM:
1. Read the complete workflow definition above
2. Check the execution log to see what's already been completed
3. Find the FIRST INCOMPLETE STEP
4. Resume from that step — do NOT re-run completed steps
5. Continue through all remaining incomplete steps

The execution log shows:
- Which steps are done
- What variables were created
- Where outputs were saved
- What was approved by the user

Use this information to understand the current state and resume correctly.
"""
        return context

    # ========== END NEW: Execution Logging ==========

    def execute(self) -> None:
        """
        Execute all workflow steps in sequence.

        Resumes from incomplete steps if execution log exists.
        Stops on first failure (unless on_error specifies otherwise).
        Prints progress and results to stdout.

        Raises:
            WorkflowError: If a step fails and on_error is "fail"
        """
        print(f"\n{'='*60}")
        print(f"Workflow: {self.variables.get('project_name', 'unnamed')}")
        print(f"Log file: {self.log_file}")
        print(f"{'='*60}\n")

        # Check for incomplete steps
        incomplete_steps = [
            s for s in self.steps if not self._was_step_completed(s.step_num)
        ]

        if self.execution_log and incomplete_steps:
            completed = len(self.steps) - len(incomplete_steps)
            print(f"Resuming workflow: {completed}/{len(self.steps)} steps completed")
            print(
                f"Starting from: Step {incomplete_steps[0].step_num} ({incomplete_steps[0].name})\n"
            )

        for step in self.steps:
            # Skip already-completed steps
            if self._was_step_completed(step.step_num):
                log_entry = self._get_step_log_entry(step.step_num)
                approval_str = (
                    f" (approved)"
                    if log_entry and log_entry.approval_status == "approved"
                    else ""
                )
                print(
                    f"[Step {step.step_num}] {step.name} (already completed{approval_str})"
                )
                continue

            try:
                self._execute_step(step)
            except WorkflowError as e:
                self._log_step_completion(step, "failed", error_message=str(e))

                if step.on_error == "fail":
                    print(f"\n✗ Workflow failed at {step}")
                    raise
                elif step.on_error == "skip":
                    print(f"\n⊘ Skipped: {step.name}")
                    continue
                elif step.on_error == "continue":
                    print(f"\n⚠ Error in {step.name}, continuing anyway")
                    continue

        print(f"\n{'='*60}")
        print("✓ Workflow complete!")
        print(f"{'='*60}\n")

    def _execute_step(self, step: WorkflowStep) -> None:
        """
        Execute a single workflow step.

        Steps:
        1. Interpolate variables in step.args
        2. Execute the tool
        3. Save output to file if requested
        4. Store output in variables if requested
        5. Request approval if required
        6. Log completion

        Args:
            step: WorkflowStep to execute

        Raises:
            WorkflowError: If execution fails
        """
        print(f"[Step {step.step_num}] {step.name}")
        if step.description:
            print(f"  {step.description}")

        # Interpolate variables in args
        try:
            interpolated_args = self._interpolate_dict(step.args, self.variables)
        except Exception as e:
            raise WorkflowError(f"Failed to interpolate args in {step.name}: {e}")

        # Execute the tool
        try:
            print(f"  Tool: {step.tool}")
            output = self.executor.execute(step.tool, **interpolated_args)
        except Exception as e:
            raise WorkflowError(f"Tool execution failed: {e}")

        # Store result
        self.results[step.step_num] = output

        # Save to file if requested
        saved_file = None
        if step.save_to_file:
            try:
                file_path = expand_path(interpolate(step.save_to_file, self.variables))
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(str(output), encoding="utf-8")
                print(f"  Saved to: {file_path}")
                saved_file = str(file_path)
            except Exception as e:
                raise WorkflowError(f"Failed to save output to file: {e}")

        # Save to variable if requested
        if step.save_output_to:
            self.variables[step.save_output_to] = output
            print(f"  Stored in: {{ {step.save_output_to} }}")

        print()

        # Approval gate
        approval_status = None
        if step.approval_required:
            approval_status = self._approval_gate(step, output)

        # Log step completion
        self._log_step_completion(
            step,
            status="completed",
            output_variable=step.save_output_to,
            output_file=saved_file,
            approval_status=approval_status,
        )

    def _approval_gate(self, step: WorkflowStep, output: Any) -> str:
        """
        Present output to user and wait for approval to continue.

        Args:
            step: Current step
            output: Output to show user

        Returns:
            "approved", "denied", or "edited"

        Raises:
            WorkflowError: If user denies approval
        """
        print(f"{'='*60}")
        print("APPROVAL REQUIRED")
        print(f"{'='*60}\n")

        if step.approval_message:
            print(step.approval_message)
        else:
            print(f"Review the output above for step: {step.name}")

        print(f"\nOutput:\n{output}\n")

        print(f"{'='*60}")
        response = input("Approve and continue? [y/n/e(dit)]: ").strip().lower()
        print()

        if response == "n":
            raise WorkflowError(f"User denied approval for {step.name}")
        elif response == "e":
            print(f"Edit the output file manually, then re-run the workflow.")
            print(f"Stored in variable: {{ {step.save_output_to} }}")
            raise WorkflowError(f"User elected to edit output for {step.name}")
        elif response != "y":
            print("Please enter 'y', 'n', or 'e'.")
            return self._approval_gate(step, output)

        return "approved"

    def _interpolate_dict(self, data: Any, variables: Dict[str, Any]) -> Any:
        """
        Recursively interpolate variables in a dict/list/string.

        Args:
            data: Data structure to interpolate (dict, list, str, or scalar)
            variables: Variables to use for interpolation

        Returns:
            Data with variables interpolated
        """
        if isinstance(data, dict):
            return {k: self._interpolate_dict(v, variables) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._interpolate_dict(item, variables) for item in data]
        elif isinstance(data, str):
            return interpolate(data, variables)
        else:
            return data

```
