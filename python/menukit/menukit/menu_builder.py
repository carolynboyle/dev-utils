"""
menukit.menu_builder - YAML-driven menu system.

Loads menu definitions from a YAML file supplied by the caller.
Renders menus, handles user selection, returns selected item ID.

Supports token substitution in display strings — tokens are supplied
by the caller, menukit does not know what they mean.

Usage:
    from menukit.menu_builder import MenuBuilder, MenuItem
    from menukit.prompts import PromptHelper

    prompt = PromptHelper()
    builder = MenuBuilder(menus_path=Path("~/.myapp/menus.yaml"), prompt_helper=prompt)

    tokens = {"editor": "vim", "version": "1.0"}
    action = builder.display_menu("main_menu", tokens=tokens)
"""

from pathlib import Path
from typing import Optional
import yaml

from menukit.prompts import PromptHelper, UserCancelled


class MenuItem:
    """Represents a single menu item."""

    def __init__(self, display: str, item_id: str):
        self.display = display
        self.item_id = item_id

    def __str__(self):
        return self.display


class MenuBuilder:
    """
    Renders menus from a YAML definition file.

    The caller supplies:
      - menus_path: where to find the menus.yaml
      - prompt_helper: a PromptHelper instance for input
      - tokens (per call): dict of substitution values for display strings
    """

    def __init__(self, menus_path: Path, prompt_helper: PromptHelper):
        self.prompt = prompt_helper
        self.menus = self._load_menus(menus_path)

    def _load_menus(self, menus_path: Path) -> dict:
        """Load menus from YAML file. Returns empty dict if file missing."""
        path = Path(menus_path).expanduser()
        if not path.exists():
            print(f"Warning: menus file not found: {path}")
            return {}
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return data or {}
        except (yaml.YAMLError, OSError) as e:
            print(f"Warning: could not load menus from {path}: {e}")
            return {}

    def display_menu(self, menu_name: str, tokens: Optional[dict] = None) -> str:
        """
        Display a named menu and return the selected item ID.

        'q' at the selection prompt always returns "back", regardless of
        whether the menu definition includes a back/quit item.

        Args:
            menu_name: Key in menus.yaml (e.g., "main_menu")
            tokens:    Optional dict of substitution values for display strings
                       e.g. {"editor": "vim", "package_manager": "apt"}

        Returns:
            str: The 'id' of the selected menu item, or "back" if cancelled.
        """
        if menu_name not in self.menus:
            print(f"Error: menu '{menu_name}' not found in menus file")
            return "back"

        menu_def = self.menus[menu_name]
        title = menu_def.get("title", "Menu")
        items_data = menu_def.get("items", [])

        if not items_data:
            print(f"Error: menu '{menu_name}' has no items")
            return "back"

        items = [
            MenuItem(self._resolve_display(item["display"], tokens or {}), item["id"])
            for item in items_data
        ]

        try:
            idx = self.prompt.choice(title, items)
            return items[idx].item_id
        except UserCancelled:
            return "back"

    def _resolve_display(self, display: str, tokens: dict) -> str:
        """
        Substitute tokens in a display string.

        Unknown tokens are left as-is rather than raising an error.

        Args:
            display: Display string, e.g. "Editor: {editor}"
            tokens:  Dict of substitution values, e.g. {"editor": "vim"}

        Returns:
            Resolved string, e.g. "Editor: vim"
        """
        try:
            return display.format(**tokens)
        except KeyError:
            return display
