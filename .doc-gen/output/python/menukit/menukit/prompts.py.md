# prompts.py

**Path:** python/menukit/menukit/prompts.py
**Syntax:** python
**Generated:** 2026-03-28 11:44:32

```python
"""
projs.prompts - Interactive prompt helpers
"""
import os
from typing import List


class UserCancelled(Exception):
    """Raised when the user types 'q' at a menu selection prompt."""


class PromptHelper:
    """Simple, homegrown prompt helpers (no external dependencies)."""

    @staticmethod
    def text(prompt: str, default: str = "") -> str:
        """Prompt for text input."""
        full_prompt = f"{prompt}"
        if default:
            full_prompt += f" [{default}]"
        full_prompt += ": "

        result = input(full_prompt).strip()
        return result if result else default

    @staticmethod
    def yes_no(prompt: str, default: bool = False) -> bool:
        """Prompt for yes/no."""
        suffix = " [Y/n]" if default else " [y/N]"
        while True:
            result = input(prompt + suffix + ": ").strip().lower()
            if result in ("y", "yes"):
                return True
            elif result in ("n", "no"):
                return False
            elif not result:
                return default
            print("Please answer 'y' or 'n'.")

    @staticmethod
    def choice(prompt: str, options: List[str]) -> int:
        """
        Prompt for single selection from list.

        Returns 0-indexed int on success.
        Raises UserCancelled if the user enters 'q'.
        """
        print(f"\n{prompt}")
        for i, option in enumerate(options, 1):
            print(f"  {i}. {option}")
        print("  q. Cancel")

        while True:
            raw = input("Selection: ").strip().lower()
            if raw == "q":
                raise UserCancelled
            try:
                result = int(raw)
                if 1 <= result <= len(options):
                    return result - 1
                print(f"Please select 1-{len(options)}, or q to cancel.")
            except ValueError:
                print("Please enter a number or q to cancel.")

    @staticmethod
    def multi_choice(prompt: str, options: List[str]) -> List[int]:
        """
        Prompt for multiple selections.

        Returns 0-indexed list on success.
        Raises UserCancelled if the user enters 'q'.
        """
        selected = [False] * len(options)

        while True:
            os.system("clear")
            print(f"\n{prompt}")
            for i, option in enumerate(options):
                marker = "[x]" if selected[i] else "[ ]"
                print(f"  {i+1}. {marker} {option}")

            print("\n  Enter number to toggle, 'done' to confirm, or q to cancel:")
            raw = input("> ").strip().lower()

            if raw == "q":
                raise UserCancelled
            elif raw == "done":
                return [i for i, s in enumerate(selected) if s]
            else:
                try:
                    idx = int(raw) - 1
                    if 0 <= idx < len(options):
                        selected[idx] = not selected[idx]
                    else:
                        print(f"Please select 1-{len(options)}.")
                except ValueError:
                    print("Please enter a number, 'done', or q.")

```
