# menu_builder.py

**Path:** python/menukit/menukit/menu_builder.py
**Syntax:** python
**Generated:** 2026-03-28 11:44:32

```python
"""
projs.menu_builder - Dynamic menu system driven by YAML configuration

Provides a universal display_menu() function that renders any menu from menus.yaml,
handles user selection, and returns the selected item ID for dispatch.

Supports token substitution in display strings:
  {editor}          — current editor from system config
  {package_manager} — current package manager from system config
"""

from typing import List

from projs.cli.prompts import PromptHelper, UserCancelled


class MenuItem:
    """Represents a single menu item."""

    def __init__(self, display: str, item_id: str):
        self.display = display
        self.item_id = item_id

    def __str__(self):
        return self.display


class MenuBuilder:
    """
    Build and display menus driven by menus.yaml configuration.

    Supports token substitution so menu items can reflect live config values
    without hardcoding them into the menu definition.
    """

    def __init__(self, config_manager, prompt_helper):
        self.config = config_manager
        self.prompt = prompt_helper

    def display_menu(self, menu_name: str) -> str:
        """
        Display a menu from menus.yaml and return the selected item ID.

        'q' at the selection prompt always returns "back", regardless of
        whether the menu definition includes a back/quit item.

        Args:
            menu_name: Key in menus.yaml (e.g., "main_menu", "settings_menu")

        Returns:
            str: The 'id' of the selected menu item, or "back" if cancelled.
        """
        if menu_name not in self.config.menus:
            print(f"Error: Menu '{menu_name}' not found in menus.yaml")
            return "back"

        menu_def = self.config.menus[menu_name]
        title = menu_def.get("title", "Menu")
        items_data = menu_def.get("items", [])

        if not items_data:
            print(f"Error: Menu '{menu_name}' has no items")
            return "back"

        # Build MenuItem objects with token substitution applied
        items = [
            MenuItem(self._resolve_display(item["display"]), item["id"])
            for item in items_data
        ]

        try:
            idx = self.prompt.choice(title, items)
            return items[idx].item_id
        except UserCancelled:
            return "back"

    def _resolve_display(self, display: str) -> str:
        """
        Resolve token substitutions in a menu item display string.

        Supported tokens:
          {editor}          — config.get_editor()
          {package_manager} — config.get_package_manager()
        """
        tokens = {
            "author": self.config.get_author() or "not set",
            "editor": self.config.get_editor() or "not set",
            "package_manager": self.config.get_package_manager(),
        }
        try:
            return display.format(**tokens)
        except KeyError:
            # Unknown token — return display string as-is
            return display

    def build_commands_menu(self) -> List[MenuItem]:
        """
        Build commands menu from the command library.

        Returns:
            List of MenuItem objects
        """
        menu_items = []
        all_commands = self.config.command_library.get_all() \
            if hasattr(self.config, "command_library") else []

        for cmd in all_commands:
            display = f"{cmd['name']}  ({cmd['command']})"
            menu_items.append(MenuItem(display, cmd["id"]))

        return menu_items

    def build_languages_menu(self) -> List[MenuItem]:
        """Build languages menu from defaults."""
        return [MenuItem(lang, lang) for lang in self.config.get_languages()]

    def build_licenses_menu(self) -> List[MenuItem]:
        """Build licenses menu from defaults."""
        return [MenuItem(lic, lic) for lic in self.config.get_licenses()]

```
