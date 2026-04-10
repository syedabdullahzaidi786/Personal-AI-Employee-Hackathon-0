"""
Unit tests for FILESYSTEM_AUTOMATION_SKILL Phase 1.

Tests cover:
  - Validator: boundary enforcement, symlink rejection, traversal rejection
  - NamingConventionParser: valid/invalid names, suggestions, folder mapping
  - FileOperations: rename, move, rollback, circuit breaker
  - SkillLogger: log file creation (smoke test)
  - FilesystemSkill: facade integration

Run with:
    python -m pytest tests/test_filesystem_automation.py -v
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Adjust sys.path so that `src/` is importable when running from repo root
# ---------------------------------------------------------------------------
import sys

from silver_tier_core_autonomy.filesystem_automation import (
    CircuitBreaker,
    FilesystemSkill,
    FileOperations,
    NamingConventionParser,
    SkillLogger,
    Validator,
)
from silver_tier_core_autonomy.filesystem_automation.validator import SecurityError, VaultError
from silver_tier_core_autonomy.filesystem_automation.operations import OperationResult


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    """Minimal vault structure inside a temp directory."""
    vault_root = tmp_path / "obsidian-vault"
    for folder in [
        "10-KNOWLEDGE/agents",
        "20-PROCESSES/workflows",
        "70-LOGS/daily",
        "70-LOGS/errors",
        "70-LOGS/operations",
        "80-MEMORY/episodic",
        "80-MEMORY/semantic",
    ]:
        (vault_root / folder).mkdir(parents=True)
    return vault_root


@pytest.fixture()
def validator(vault: Path) -> Validator:
    return Validator(vault)


@pytest.fixture()
def logger(vault: Path) -> SkillLogger:
    return SkillLogger(vault)


@pytest.fixture()
def ops(validator: Validator, logger: SkillLogger) -> FileOperations:
    return FileOperations(validator=validator, logger=logger)


@pytest.fixture()
def skill(vault: Path) -> FilesystemSkill:
    return FilesystemSkill(vault_root=vault)


# ===========================================================================
# Validator
# ===========================================================================

class TestValidator:

    def test_valid_path_inside_vault(self, validator: Validator, vault: Path) -> None:
        target = vault / "10-KNOWLEDGE" / "agents" / "001-test.md"
        target.touch()
        resolved = validator.validate_path(target)
        assert resolved == target.resolve()

    def test_rejects_path_outside_vault(self, validator: Validator, tmp_path: Path) -> None:
        outside = tmp_path / "outside.md"
        outside.touch()
        with pytest.raises(SecurityError, match="outside vault boundary"):
            validator.validate_path(outside)

    def test_rejects_parent_traversal(self, validator: Validator, vault: Path) -> None:
        evil = vault / ".." / "outside.md"
        with pytest.raises(SecurityError, match="Parent traversal"):
            validator.validate_path(evil)

    def test_rejects_forbidden_prefix_git(self, validator: Validator, vault: Path) -> None:
        (vault / ".git").mkdir()
        target = vault / ".git" / "config"
        target.touch()
        with pytest.raises(SecurityError, match="forbidden"):
            validator.validate_path(target)

    def test_preflight_raises_when_source_missing(self, validator: Validator, vault: Path) -> None:
        missing = vault / "10-KNOWLEDGE" / "ghost.md"
        with pytest.raises(FileNotFoundError):
            validator.preflight(missing)

    def test_preflight_raises_when_dest_parent_missing(self, validator: Validator, vault: Path) -> None:
        src = vault / "10-KNOWLEDGE" / "001-test.md"
        src.touch()
        dst = vault / "99-NONEXISTENT" / "001-test.md"
        with pytest.raises(VaultError, match="does not exist"):
            validator.preflight(src, dst)

    def test_preflight_raises_when_dest_exists(self, validator: Validator, vault: Path) -> None:
        src = vault / "10-KNOWLEDGE" / "001-source.md"
        dst = vault / "10-KNOWLEDGE" / "agents" / "001-dest.md"
        src.touch()
        dst.touch()
        with pytest.raises(FileExistsError):
            validator.preflight(src, dst)

    def test_vault_structure_ok(self, validator: Validator) -> None:
        assert validator.vault_structure_ok() is True

    def test_is_valid_markdown(self, validator: Validator, vault: Path) -> None:
        md = vault / "10-KNOWLEDGE" / "001-test.md"
        md.touch()
        assert validator.is_valid_markdown(md) is True
        non_md = vault / "10-KNOWLEDGE" / "file.txt"
        non_md.touch()
        assert validator.is_valid_markdown(non_md) is False


# ===========================================================================
# NamingConventionParser
# ===========================================================================

class TestNamingConventionParser:

    @pytest.fixture(autouse=True)
    def parser(self) -> None:
        self.p = NamingConventionParser()

    # Valid names
    @pytest.mark.parametrize("name", [
        "001-customer-agent.md",
        "042-email-automation-workflow.md",
        "WF-001-customer-onboarding.md",
        "EP-20260216-meeting-notes.md",
        "SM-023-pricing-strategy.md",
        "2026-02-16.md",
    ])
    def test_valid_names(self, name: str) -> None:
        result = self.p.validate(name)
        assert result.valid, f"Expected valid, got violations: {result.violations}"

    # Invalid names
    @pytest.mark.parametrize("name,expected_violation_fragment", [
        ("Customer Agent.MD",        "Extension"),
        ("Customer Agent.md",        "Spaces"),
        ("customer_agent.md",        "Underscores"),
        ("CustomerAgent.md",         "does not match"),
        ("a" * 51 + ".md",           "too long"),
    ])
    def test_invalid_names(self, name: str, expected_violation_fragment: str) -> None:
        result = self.p.validate(name)
        assert not result.valid
        assert any(
            expected_violation_fragment.lower() in v.lower()
            for v in result.violations
        ), f"Expected '{expected_violation_fragment}' in {result.violations}"

    def test_suggestion_produced_for_invalid(self) -> None:
        result = self.p.validate("My Meeting Notes.MD")
        assert result.suggested_name is not None
        assert " " not in result.suggested_name
        assert result.suggested_name.endswith(".md")

    def test_suggest_folder_workflow(self) -> None:
        assert self.p.suggest_folder("WF-001-onboarding.md") == "20-PROCESSES/workflows"

    def test_suggest_folder_episodic(self) -> None:
        assert self.p.suggest_folder("EP-20260216-meeting.md") == "80-MEMORY/episodic"

    def test_suggest_folder_daily_log(self) -> None:
        assert self.p.suggest_folder("2026-02-16.md") == "70-LOGS/daily"

    def test_suggest_folder_unknown_returns_none(self) -> None:
        assert self.p.suggest_folder("unknown-file.md") is None

    def test_next_id_empty_folder(self, tmp_path: Path) -> None:
        folder = tmp_path / "agents"
        folder.mkdir()
        assert self.p.next_id(folder) == "001"

    def test_next_id_with_existing_files(self, tmp_path: Path) -> None:
        folder = tmp_path / "agents"
        folder.mkdir()
        (folder / "001-first.md").touch()
        (folder / "002-second.md").touch()
        assert self.p.next_id(folder) == "003"


# ===========================================================================
# FileOperations
# ===========================================================================

class TestFileOperations:

    def test_rename_success(self, ops: FileOperations, vault: Path) -> None:
        src = vault / "10-KNOWLEDGE" / "001-test-file.md"
        src.write_text("# Hello")
        result = ops.rename(src, "002-renamed-file.md")
        assert result.success
        assert (vault / "10-KNOWLEDGE" / "002-renamed-file.md").exists()
        assert not src.exists()

    def test_rename_preserves_content(self, ops: FileOperations, vault: Path) -> None:
        content = "# Important\nKeep this safe."
        src = vault / "10-KNOWLEDGE" / "001-orig.md"
        src.write_text(content)
        ops.rename(src, "001-renamed.md")
        dst = vault / "10-KNOWLEDGE" / "001-renamed.md"
        assert dst.read_text() == content

    def test_move_success(self, ops: FileOperations, vault: Path) -> None:
        src = vault / "10-KNOWLEDGE" / "001-source.md"
        src.write_text("data")
        dst = vault / "80-MEMORY" / "episodic" / "EP-20260216-source.md"
        result = ops.move(src, dst)
        assert result.success
        assert dst.exists()
        assert not src.exists()

    def test_rename_to_existing_fails(self, ops: FileOperations, vault: Path) -> None:
        src = vault / "10-KNOWLEDGE" / "001-a.md"
        existing = vault / "10-KNOWLEDGE" / "001-b.md"
        src.write_text("a")
        existing.write_text("b")
        result = ops.rename(src, "001-b.md")
        assert not result.success
        assert src.exists(), "Source should still exist after failed rename"

    def test_dry_run_does_not_move(self, validator: Validator, logger: SkillLogger, vault: Path) -> None:
        dry_ops = FileOperations(validator=validator, logger=logger, dry_run=True)
        src = vault / "10-KNOWLEDGE" / "001-dry.md"
        src.write_text("stay here")
        dst = vault / "80-MEMORY" / "episodic" / "EP-20260216-dry.md"
        result = dry_ops.move(src, dst)
        assert result.success
        assert src.exists(), "Dry-run should not move file"
        assert not dst.exists()
        assert "[DRY RUN]" in result.message

    def test_add_frontmatter(self, ops: FileOperations, vault: Path) -> None:
        target = vault / "10-KNOWLEDGE" / "001-no-front.md"
        target.write_text("# Just content\nBody text.\n")
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = ops.add_frontmatter(
            path=target,
            file_id="no-front",
            name="No Front",
            doc_type="document",
            tags=["test"],
            created_iso=now,
            updated_iso=now,
        )
        assert result.success
        text = target.read_text()
        assert text.startswith("---")
        assert "id: no-front" in text
        assert "# Just content" in text

    def test_add_frontmatter_idempotent(self, ops: FileOperations, vault: Path) -> None:
        target = vault / "10-KNOWLEDGE" / "001-has-front.md"
        target.write_text("---\nid: existing\n---\n# Content\n")
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = ops.add_frontmatter(
            path=target,
            file_id="existing",
            name="Existing",
            doc_type="document",
            tags=[],
            created_iso=now,
            updated_iso=now,
        )
        assert result.success
        text = target.read_text()
        # Should not have doubled frontmatter
        assert text.count("---") == 2


# ===========================================================================
# CircuitBreaker
# ===========================================================================

class TestCircuitBreaker:

    def test_starts_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == "CLOSED"
        assert cb.allow_request()

    def test_opens_after_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "OPEN"
        assert not cb.allow_request()

    def test_success_resets_failures(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.allow_request()


# ===========================================================================
# SkillLogger
# ===========================================================================

class TestSkillLogger:

    def test_info_creates_log_file(self, logger: SkillLogger, vault: Path) -> None:
        logger.info("Test info message")
        daily_dir = vault / "70-LOGS" / "daily"
        log_files = list(daily_dir.glob("*.md"))
        assert len(log_files) >= 1

    def test_warn_appends_to_daily_log(self, logger: SkillLogger, vault: Path) -> None:
        logger.warn("Test warning")
        daily_dir = vault / "70-LOGS" / "daily"
        content = "".join(f.read_text() for f in daily_dir.glob("*.md"))
        assert "WARN" in content

    def test_error_creates_error_log(self, logger: SkillLogger, vault: Path) -> None:
        logger.error("Test error")
        error_dir = vault / "70-LOGS" / "errors"
        log_files = list(error_dir.glob("*.md"))
        assert len(log_files) >= 1

    def test_audit_creates_ops_log(self, logger: SkillLogger, vault: Path) -> None:
        logger.audit("test-op", {"file_before": "a.md", "file_after": "b.md", "result": "success"})
        ops_dir = vault / "70-LOGS" / "operations"
        log_files = list(ops_dir.glob("*.md"))
        assert len(log_files) >= 1


# ===========================================================================
# FilesystemSkill (Facade)
# ===========================================================================

class TestFilesystemSkill:

    def test_audit_file_valid_name(self, skill: FilesystemSkill, vault: Path) -> None:
        f = vault / "10-KNOWLEDGE" / "001-test.md"
        f.write_text("---\nid: test\n---\n# Test\n")
        report = skill.audit_file(f)
        assert report["name_valid"] is True
        assert report["violations"] == []
        assert report["has_frontmatter"] is True

    def test_audit_file_invalid_name(self, skill: FilesystemSkill, vault: Path) -> None:
        f = vault / "10-KNOWLEDGE" / "Bad Name.md"
        f.write_text("# Bad")
        report = skill.audit_file(f)
        assert report["name_valid"] is False
        assert len(report["violations"]) > 0
        assert report["suggested_name"] is not None

    def test_rename_file_end_to_end(self, skill: FilesystemSkill, vault: Path) -> None:
        src = vault / "10-KNOWLEDGE" / "001-original.md"
        src.write_text("# Content")
        result = skill.rename_file(src, "002-new-name.md")
        assert result.success
        assert (vault / "10-KNOWLEDGE" / "002-new-name.md").exists()

    def test_validate_path_accepts_vault_file(self, skill: FilesystemSkill, vault: Path) -> None:
        f = vault / "10-KNOWLEDGE" / "001-valid.md"
        f.touch()
        resolved = skill.validate_path(f)
        assert resolved == f.resolve()

    def test_validate_path_rejects_outside(self, skill: FilesystemSkill, tmp_path: Path) -> None:
        outside = tmp_path / "sneaky.md"
        outside.touch()
        with pytest.raises(SecurityError):
            skill.validate_path(outside)
