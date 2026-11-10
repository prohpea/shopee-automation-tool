"""
Shopee Automation Tool - Session & Cookie Manager.
Saves, loads, and validates browser storage state (cookies, tokens, localStorage).
"""

import json
from pathlib import Path
from typing import Optional
from playwright.async_api import BrowserContext
from .config import settings
from ..utils.logger import logger


class SessionManager:
    """Manages browser session states, saved cookies, and authentication state persistence."""

    def __init__(self, session_name: Optional[str] = None):
        self.session_name = session_name or settings.default_session_name
        self.session_path = settings.get_session_path(self.session_name)

    def exists(self) -> bool:
        """Checks if a saved session file exists on disk."""
        return self.session_path.exists() and self.session_path.stat().st_size > 0

    async def save_session(self, context: BrowserContext) -> Path:
        """Exports the context storage state (cookies + localStorage) to JSON file."""
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(self.session_path))
        logger.info(
            f"[bold green]✓ Session state saved successfully to: {self.session_path}[/bold green]"
        )
        return self.session_path

    def get_storage_state_path(self) -> Optional[str]:
        """Returns the storage state file path string if valid, else None."""
        if self.exists():
            return str(self.session_path)
        return None

    def read_cookies(self) -> list:
        """Reads and returns the list of cookies from the saved session file."""
        if not self.exists():
            return []
        try:
            with open(self.session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("cookies", [])
        except Exception as e:
            logger.error(f"Error reading session file {self.session_path}: {e}")
            return []

    def get_shopee_token(self) -> Optional[str]:
        """Extracts authentication token (SPC_EC or shopee_token) from saved cookies."""
        cookies = self.read_cookies()
        for cookie in cookies:
            if cookie.get("name") in ("SPC_EC", "SPC_ST", "SPC_T_IV", "SPC_T_ID"):
                return cookie.get("value")
        return None

    def delete_session(self) -> bool:
        """Deletes the current session file."""
        if self.exists():
            try:
                self.session_path.unlink()
                logger.info(f"Deleted session file: {self.session_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete session file: {e}")
                return False
        return False
