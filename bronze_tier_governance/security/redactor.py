"""
SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL — Secret Redactor
Masks sensitive values from strings and dicts before logging.

Constitution compliance:
  - Section 8: "Never log credential values"
  - Principle VI: Fail Safe — redaction must never raise; on error return safe fallback
"""

from __future__ import annotations

import re
from typing import Any


# Replacement token used in place of redacted values
REDACTED = "[REDACTED]"

# Patterns that indicate a secret value follows (key=value style)
_SECRET_KEY_RE = re.compile(
    r"(password|passwd|secret|token|api.?key|apikey|auth|credential|"
    r"private.?key|access.?key|bearer|client.?secret|webhook)",
    re.IGNORECASE,
)

# Patterns for high-entropy / well-known secret value shapes
_VALUE_PATTERNS: list[tuple[str, re.Pattern]] = [
    # AWS access/secret keys
    ("aws_access_key",  re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret_key",  re.compile(r"\b[A-Za-z0-9/+=]{40}\b")),
    # Generic bearer tokens (long alphanumeric)
    ("bearer_token",    re.compile(r"\bey[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b")),
    # GitHub tokens
    ("github_token",    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    # Generic API keys (32+ hex chars)
    ("generic_api_key", re.compile(r"\b[0-9a-fA-F]{32,64}\b")),
    # Slack tokens
    ("slack_token",     re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]+")),
]


class SecretRedactor:
    """
    Redacts secret values from strings, dicts, and log lines.

    Usage::

        redactor = SecretRedactor()
        redactor.register_secret("my_api_key_value")  # register known secret

        safe = redactor.redact("API_KEY=abc123xyz my_api_key_value is secret")
        # → "API_KEY=[REDACTED] [REDACTED] is secret"
    """

    def __init__(self) -> None:
        # Literal secret values registered at runtime (sorted longest-first for correctness)
        self._known_secrets: list[str] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_secret(self, value: str) -> None:
        """Register a literal secret value for redaction."""
        if not value or len(value) < 4:
            return  # Too short to reliably redact
        if value not in self._known_secrets:
            self._known_secrets.append(value)
            # Keep longest values first so longer matches take priority
            self._known_secrets.sort(key=len, reverse=True)

    def unregister_all(self) -> None:
        """Clear all registered secrets (e.g. after credential rotation)."""
        self._known_secrets.clear()

    # ------------------------------------------------------------------
    # Redaction
    # ------------------------------------------------------------------

    def redact(self, text: str) -> str:
        """
        Redact secrets from *text*.

        Applies (in order):
          1. Literal known-secret substitution
          2. ``key=value`` pattern redaction
          3. Well-known value-shape redaction
        """
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:  # noqa: BLE001
                return REDACTED

        try:
            result = self._redact_known(text)
            result = self._redact_key_value(result)
            result = self._redact_value_patterns(result)
            return result
        except Exception:  # noqa: BLE001
            return REDACTED

    def redact_dict(self, d: Any, depth: int = 0) -> Any:
        """
        Recursively redact a dict/list/str.

        Keys matching secret-name patterns have their values fully replaced.
        """
        if depth > 10:
            return REDACTED
        try:
            if isinstance(d, dict):
                return {
                    k: (REDACTED if _SECRET_KEY_RE.search(str(k)) else self.redact_dict(v, depth + 1))
                    for k, v in d.items()
                }
            if isinstance(d, list):
                return [self.redact_dict(item, depth + 1) for item in d]
            if isinstance(d, str):
                return self.redact(d)
            return d
        except Exception:  # noqa: BLE001
            return REDACTED

    def is_safe(self, text: str) -> bool:
        """Return True if *text* contains no detectable secrets."""
        return self.redact(text) == text

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _redact_known(self, text: str) -> str:
        for secret in self._known_secrets:
            text = text.replace(secret, REDACTED)
        return text

    def _redact_key_value(self, text: str) -> str:
        """Redact patterns like ``SECRET=abc123`` or ``"password": "xyz"``."""
        # Covers: KEY=VALUE, KEY: VALUE, "KEY": "VALUE"
        pattern = re.compile(
            r'(?i)(?P<key>(?:password|passwd|secret|token|api.?key|apikey|auth(?:orization)?|'
            r'credential|private.?key|access.?key|bearer|client.?secret|webhook))'
            r'(?P<sep>\s*[=:]\s*["\']?)'
            r'(?P<val>[^\s"\'&,\}\]\n]+)',
        )
        return pattern.sub(lambda m: m.group("key") + m.group("sep") + REDACTED, text)

    def _redact_value_patterns(self, text: str) -> str:
        for _, pattern in _VALUE_PATTERNS:
            text = pattern.sub(REDACTED, text)
        return text


# ---------------------------------------------------------------------------
# Module-level convenience instance
# ---------------------------------------------------------------------------

_default_redactor = SecretRedactor()


def redact(text: str) -> str:
    """Redact secrets from *text* using the default module redactor."""
    return _default_redactor.redact(text)


def redact_dict(d: Any) -> Any:
    """Redact secrets from *d* using the default module redactor."""
    return _default_redactor.redact_dict(d)


def register_secret(value: str) -> None:
    """Register a literal secret with the default module redactor."""
    _default_redactor.register_secret(value)
