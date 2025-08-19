"""
cli_utils.py
------------
Terminal UI helpers for menu navigation and input validation.
"""

import os

def pause_for_user(message: str = "Press Enter to continue...") -> None:
    input(message)

def clear_screen() -> None:
    """Clear terminal screen on all platforms."""
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
    except Exception:
        print("\n" * 50)

def show_operation_header(operation_name: str) -> None:
    print(f"\n=== {operation_name} ===")

def get_user_confirmation(message: str, default: str = 'n') -> bool:
    """Return True if user confirms with Y."""
    prompt = f"{message} ({'Y/n' if default.lower() == 'y' else 'y/N'}): "
    response = input(prompt).strip().lower()
    if not response:
        response = default.lower()
    return response == 'y'

def get_non_empty_input(prompt_message: str, allow_cancel: bool = True) -> str | None:
    """Prompt until non-empty input is provided, or return None on cancel."""
    while True:
        try:
            value = input(prompt_message).strip()
            if value:
                return value
            print("Input cannot be empty. Please try again.")
        except KeyboardInterrupt:
            if allow_cancel:
                print("\nOperation cancelled.")
                return None

def get_valid_integer_choice(prompt_message: str, min_choice: int, max_choice: int, allow_cancel: bool = True) -> int | None:
    """Prompt until valid integer within range is provided."""
    full_prompt = f"{prompt_message} [{min_choice}-{max_choice}]: "
    while True:
        try:
            raw = input(full_prompt).strip()
            try:
                choice = int(raw)
                if min_choice <= choice <= max_choice:
                    return choice
                print(f"Invalid choice. Enter a number between {min_choice} and {max_choice}.")
            except ValueError:
                print(f"Invalid input. Enter a number between {min_choice} and {max_choice}.")
        except KeyboardInterrupt:
            if allow_cancel:
                print("\nOperation cancelled.")
                return None
