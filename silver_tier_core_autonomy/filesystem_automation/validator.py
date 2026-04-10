"""
FILESYSTEM_AUTOMATION_SKILL — Validator
Phase 1: Vault boundary enforcement and pre-flight checks.

Constitution compliance:
  - Principle VI: Fail Safe, Fail Visible
  - Section 7: Vault Governance (boundary enforcement)
"""

import os
import re
from pathlib import Path
from typing import Optional


class SecurityError(Exception):
    """Raised when a security boundary would be violated."""


class VaultError(Exception):
    """Raised when vault structure is invalid or inaccessible."""


class Validator:
    """
    Enforces vault boundary rules and pre-flight checks before
    any filesystem operation is attempted.

    Rules:
      - All paths must resolve inside vault_root
      - No symlinks allowed
      - No parent-directory traversal (..)
      - Forbidden path prefixes: .git, .obsidian, .claude, .specify
    """

    FORBIDDEN_PREFIXES = (".git", ".obsidian", ".claude", ".specify")

    def __init__(self, vault_root: str | Path) -> None:
        self.vault_root = Path(vault_root).resolve()
        if not self.vault_root.is_dir():
            raise VaultError(f"Vault root does not exist: {self.vault_root}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_path(self, path: str | Path) -> Path:
        """
        Resolve *path* and assert it lives inside the vault.

        Returns the resolved absolute Path on success.
        Raises SecurityError or VaultError on failure.
        """
        raw = Path(path)

        # Reject parent-directory traversal early (before resolve)
        if ".." in raw.parts:
            raise SecurityError(f"Parent traversal not allowed: {path}")

        resolved = raw.resolve()

        # Symlink check
        if raw.is_symlink():
            raise SecurityError(f"Symlinks not allowed: {path}")

        # Boundary check
        try:
            resolved.relative_to(self.vault_root)
        except ValueError:
            raise SecurityError(
                f"Path outside vault boundary: {resolved} "
                f"(vault: {self.vault_root})"
            )

        # Forbidden prefix check (relative to vault root)
        rel = resolved.relative_to(self.vault_root)
        first_part = rel.parts[0] if rel.parts else ""
        if first_part in self.FORBIDDEN_PREFIXES:
            raise SecurityError(
                f"Operations on '{first_part}/' are forbidden: {resolved}"
            )

        return resolved

    def preflight(
        self,
        source: str | Path,
        destination: Optional[str | Path] = None,
    ) -> tuple[Path, Optional[Path]]:
        """
        Run pre-flight checks for a move/rename operation.

        Validates:
          - source exists and is readable
          - source is within vault
          - destination (if given) is within vault and has no name conflict
          - destination parent directory exists

        Returns (resolved_source, resolved_destination).
        Raises SecurityError, VaultError, or FileNotFoundError on failure.
        """
        src = self.validate_path(source)

        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")
        if not os.access(src, os.R_OK):
            raise PermissionError(f"Source file not readable: {src}")

        dst: Optional[Path] = None
        if destination is not None:
            dst = self.validate_path(destination)
            if not dst.parent.exists():
                raise VaultError(
                    f"Destination directory does not exist: {dst.parent}"
                )
            if dst.exists():
                raise FileExistsError(
                    f"Destination already exists: {dst}"
                )

        return src, dst

    def is_valid_markdown(self, path: str | Path) -> bool:
        """Return True if *path* is a readable file with .md extension."""
        p = Path(path)
        return p.suffix.lower() == ".md" and p.is_file() and os.access(p, os.R_OK)

    def vault_structure_ok(self) -> bool:
        """Quick sanity-check that the vault root is still accessible."""
        return self.vault_root.is_dir() and os.access(self.vault_root, os.R_OK | os.W_OK)
