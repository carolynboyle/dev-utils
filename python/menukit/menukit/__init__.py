"""
menukit - YAML-driven menu system and input plugin interface.

A portable, data-driven menu system for CLI applications.
Menu definitions live in YAML files, not in code.

Usage:
    from menukit import MenuBuilder, MenuItem, PromptHelper, UserCancelled
    from menukit import InputPlugin
"""

from menukit.menu_builder import MenuBuilder, MenuItem
from menukit.prompts import PromptHelper, UserCancelled
from menukit.input_plugin import InputPlugin

__version__ = "0.1.0"
__all__ = [
    "MenuBuilder",
    "MenuItem",
    "PromptHelper",
    "UserCancelled",
    "InputPlugin",
]
