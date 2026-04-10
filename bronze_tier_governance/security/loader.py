"""
SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL — Credential Loader
Loads secrets from environment variables and .env files.

Constitution compliance:
  - Section 8: "All secrets in .env file (gitignored), load at runtime only"
  - "Never log credential values"

Design:
  - Secrets are returned as plain strings to the caller.
  - The loader itself NEVER stores the secret values beyond the return call.
  - Values are registered with the default redactor on load.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from .redactor import register_secret


class CredentialError(Exception):
    """Raised when a required credential cannot be loaded."""


class DotEnvParser:
    """
    Minimal .env file parser — no external dependencies required.

    Supports:
      - ``KEY=value``
      - ``KEY="quoted value"``
      - ``# comments``
      - ``export KEY=value``
      - Multi-line values with backslash continuation
    """

    _LINE_RE = re.compile(
        r"""^\s*(?:export\s+)?"""
        r"""(?P<key>[A-Za-z_][A-Za-z0-9_]*)"""
        r"""=(?P<value>.*)$"""
    )

    @classmethod
    def parse(cls, content: str) -> dict[str, str]:
        result: dict[str, str] = {}
        lines  = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            # Handle backslash continuation
            while line.endswith("\\") and i + 1 < len(lines):
                line = line[:-1] + lines[i + 1]
                i += 1
            line = line.strip()
            i += 1
            if not line or line.startswith("#"):
                continue
            m = cls._LINE_RE.match(line)
            if not m:
                continue
            key   = m.group("key")
            value = m.group("value").strip()
            # Strip surrounding quotes (single or double)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            result[key] = value
        return result


class CredentialLoader:
    """
    Loads credential values from the OS environment and/or .env files.

    Secrets are NEVER stored in this object — they are returned to the caller
    and registered with the SecretRedactor so they are masked in logs.

    Usage::

        loader = CredentialLoader()
        loader.load_dotenv(".env")             # parse .env into os.environ
        value = loader.require("GMAIL_API_KEY") # raises CredentialError if missing
        values = loader.require_all(["A", "B"]) # returns {key: value}
    """

    def __init__(self) -> None:
        self._loaded_keys: set[str] = set()   # Track which keys were loaded (not values)

    # ------------------------------------------------------------------
    # .env file loading
    # ------------------------------------------------------------------

    def load_dotenv(
        self,
        path: str | Path = ".env",
        *,
        override: bool = False,
    ) -> list[str]:
        """
        Parse *path* and inject variables into ``os.environ``.

        Returns the list of keys that were loaded.

        Parameters
        ----------
        override:
            If ``False`` (default), skip keys already set in the environment.
        """
        path = Path(path)
        if not path.exists():
            raise CredentialError(f".env file not found: {path}")

        content = path.read_text(encoding="utf-8")
        parsed  = DotEnvParser.parse(content)
        loaded  = []

        for key, value in parsed.items():
            if not override and key in os.environ:
                continue
            os.environ[key] = value
            register_secret(value)  # Mask in logs
            self._loaded_keys.add(key)
            loaded.append(key)

        return loaded

    def load_dotenv_safe(
        self,
        path: str | Path = ".env",
        *,
        override: bool = False,
    ) -> list[str]:
        """Like ``load_dotenv`` but returns empty list instead of raising on missing file."""
        try:
            return self.load_dotenv(path, override=override)
        except CredentialError:
            return []

    # ------------------------------------------------------------------
    # Value retrieval
    # ------------------------------------------------------------------

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a credential value from the OS environment.

        The value is registered with the redactor. Returns *default* if missing.
        """
        value = os.environ.get(key, default)
        if value is not None and value is not default:
            register_secret(value)
        return value

    def require(self, key: str) -> str:
        """
        Get a required credential. Raises ``CredentialError`` if not set or empty.
        """
        value = os.environ.get(key)
        if not value:
            raise CredentialError(
                f"Required credential '{key}' is not set in environment. "
                f"Add it to your .env file."
            )
        register_secret(value)
        return value

    def require_all(self, keys: list[str]) -> dict[str, str]:
        """
        Require multiple credentials. Raises ``CredentialError`` listing all missing keys.
        """
        missing = [k for k in keys if not os.environ.get(k)]
        if missing:
            raise CredentialError(
                f"Required credentials not set: {missing}. "
                f"Add them to your .env file."
            )
        return {k: self.require(k) for k in keys}

    def is_set(self, key: str) -> bool:
        """Return True if the key is set and non-empty in the environment."""
        return bool(os.environ.get(key))

    def check_all_set(self, keys: list[str]) -> dict[str, bool]:
        """Return {key: is_set} for each key — does NOT expose values."""
        return {k: self.is_set(k) for k in keys}

    # ------------------------------------------------------------------
    # Introspection (safe — no values)
    # ------------------------------------------------------------------

    def loaded_keys(self) -> list[str]:
        """Return list of env keys loaded via load_dotenv (not their values)."""
        return sorted(self._loaded_keys)

    def missing_keys(self, required: list[str]) -> list[str]:
        """Return keys from *required* that are not set in the environment."""
        return [k for k in required if not self.is_set(k)]
