"""
FILESYSTEM_AUTOMATION_SKILL — Phase 1
Vault file organization: validation, naming, safe operations, logging.

Public surface:

    from skills.core.filesystem_automation import FilesystemSkill

    skill = FilesystemSkill(vault_root="/path/to/obsidian-vault")
    result = skill.rename_file("vault/bad name.MD", "001-good-name.md")
    result = skill.move_file("vault/root/file.md", "vault/10-KNOWLEDGE/001-file.md")
    report = skill.audit_file("vault/some-file.md")
"""

from .logger import SkillLogger
from .naming import NamingConventionParser
from .operations import CircuitBreaker, FileOperations, OperationResult
from .validator import SecurityError, Validator, VaultError
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone


class FilesystemSkill:
    """
    High-level facade for FILESYSTEM_AUTOMATION_SKILL Phase 1.

    Composes: Validator + NamingConventionParser + FileOperations + SkillLogger.
    """

    def __init__(self, vault_root: str | Path, dry_run: bool = False) -> None:
        vault = Path(vault_root)
        self._validator = Validator(vault)
        self._naming    = NamingConventionParser()
        self._logger    = SkillLogger(vault)
        self._cb        = CircuitBreaker()
        self._ops       = FileOperations(
            validator=self._validator,
            logger=self._logger,
            circuit_breaker=self._cb,
            dry_run=dry_run,
        )

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def rename_file(self, source: str | Path, new_name: str) -> OperationResult:
        """Rename *source* to *new_name* within the same directory."""
        result = self._naming.validate(new_name)
        if not result.valid:
            self._logger.warn(
                f"Rename requested with non-compliant name '{new_name}': "
                + "; ".join(result.violations)
            )
        return self._ops.rename(source, new_name)

    def move_file(self, source: str | Path, destination: str | Path) -> OperationResult:
        """Move *source* to *destination* (full path including filename)."""
        return self._ops.move(source, destination)

    def add_frontmatter(
        self,
        path: str | Path,
        *,
        doc_type: str = "document",
        tags: Optional[list[str]] = None,
    ) -> OperationResult:
        """Prepend YAML frontmatter to *path* if missing."""
        p = Path(path)
        now_iso = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        file_id = p.stem
        name = p.stem.replace("-", " ").title()
        return self._ops.add_frontmatter(
            path=p,
            file_id=file_id,
            name=name,
            doc_type=doc_type,
            tags=tags or [],
            created_iso=now_iso,
            updated_iso=now_iso,
        )

    # ------------------------------------------------------------------
    # Analysis / reporting
    # ------------------------------------------------------------------

    def audit_file(self, path: str | Path) -> dict:
        """
        Non-destructive analysis of a single file.
        Returns a dict with naming issues and suggestions.
        """
        p = Path(path)
        naming_result = self._naming.validate(p.name)
        suggested_folder = self._naming.suggest_folder(p.name)

        return {
            "file": str(p),
            "name_valid": naming_result.valid,
            "violations": naming_result.violations,
            "suggested_name": naming_result.suggested_name,
            "suggested_folder": suggested_folder,
            "has_frontmatter": self._check_frontmatter(p),
        }

    def validate_path(self, path: str | Path) -> Path:
        """Expose path validation for external callers."""
        return self._validator.validate_path(path)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _check_frontmatter(self, p: Path) -> bool:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            return text.lstrip().startswith("---")
        except OSError:
            return False


__all__ = [
    "FilesystemSkill",
    "Validator",
    "NamingConventionParser",
    "FileOperations",
    "SkillLogger",
    "CircuitBreaker",
    "OperationResult",
    "SecurityError",
    "VaultError",
]
