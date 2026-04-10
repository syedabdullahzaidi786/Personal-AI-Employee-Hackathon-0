"""
Unit tests for Silver Tier — Plan.md Reasoning Loop.
Covers: models, analyzer, writer, loop.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from silver_tier_core_autonomy.plan_loop.models import (
    PlanDocument,
    PlanItem,
    PlanStep,
    PlanStatus,
    StepPriority,
)
from silver_tier_core_autonomy.plan_loop.analyzer import PlanAnalyzer, _infer_priority, _extract_tags
from silver_tier_core_autonomy.plan_loop.writer import PlanWriter
from silver_tier_core_autonomy.plan_loop.loop import PlanLoop, PlanLoopResult
from silver_tier_core_autonomy.plan_loop.logger import PlanLogger


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Minimal vault structure."""
    (tmp_path / "Inbox").mkdir()
    (tmp_path / "Needs_Action").mkdir()
    (tmp_path / "Plans").mkdir()
    (tmp_path / "Done").mkdir()
    return tmp_path


@pytest.fixture
def analyzer() -> PlanAnalyzer:
    return PlanAnalyzer()


@pytest.fixture
def writer(tmp_vault: Path) -> PlanWriter:
    return PlanWriter(tmp_vault)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestPlanStep:
    def test_to_markdown_contains_title(self):
        step = PlanStep(id="1", title="Send weekly report")
        md = step.to_markdown()
        assert "Send weekly report" in md
        assert "Step 1" in md

    def test_to_markdown_shows_priority(self):
        step = PlanStep(id="1", title="Urgent fix", priority=StepPriority.HIGH)
        md = step.to_markdown()
        assert "high" in md

    def test_to_markdown_shows_dependencies(self):
        step = PlanStep(id="2", title="Follow up", depends_on=["1"])
        md = step.to_markdown()
        assert "depends_on" in md
        assert "1" in md


class TestPlanDocument:
    def test_to_markdown_has_frontmatter(self):
        doc = PlanDocument(title="Test Plan")
        md = doc.to_markdown()
        assert md.startswith("---")
        assert "id:" in md
        assert "status: pending" in md

    def test_to_markdown_has_goal_section(self):
        doc = PlanDocument(title="My Plan", goal="Finish the project")
        md = doc.to_markdown()
        assert "## Goal" in md
        assert "Finish the project" in md

    def test_to_markdown_has_steps_section(self):
        doc = PlanDocument(
            title="Plan",
            steps=[PlanStep(id="1", title="Do it")],
        )
        md = doc.to_markdown()
        assert "## Steps" in md
        assert "Do it" in md

    def test_plan_id_prefix(self):
        doc = PlanDocument()
        assert doc.plan_id.startswith("PLAN-")

    def test_default_status_pending(self):
        doc = PlanDocument()
        assert doc.status == PlanStatus.PENDING


# ---------------------------------------------------------------------------
# Analyzer tests
# ---------------------------------------------------------------------------

class TestInferPriority:
    def test_urgent_keyword_gives_high(self):
        assert _infer_priority("This is urgent!") == StepPriority.HIGH

    def test_critical_keyword_gives_high(self):
        assert _infer_priority("Critical bug fix") == StepPriority.HIGH

    def test_someday_gives_low(self):
        assert _infer_priority("Someday I should refactor") == StepPriority.LOW

    def test_neutral_gives_medium(self):
        assert _infer_priority("Write documentation") == StepPriority.MEDIUM


class TestExtractTags:
    def test_hashtag_extracted(self):
        tags = _extract_tags("Fix #bug in #login", "title")
        assert "bug" in tags
        assert "login" in tags

    def test_always_includes_plan(self):
        tags = _extract_tags("no hashtags here", "no hashtags")
        assert "plan" in tags

    def test_always_includes_ai_generated(self):
        tags = _extract_tags("", "")
        assert "ai-generated" in tags

    def test_deduplication(self):
        tags = _extract_tags("#task #task", "")
        assert tags.count("task") == 1


class TestPlanAnalyzer:
    def test_analyze_returns_plan_document(self, analyzer, tmp_path):
        item = PlanItem(
            source_path=tmp_path / "test.md",
            title="Fix login bug",
            content="There is a critical bug in the login form. Need to review and fix.",
        )
        doc = analyzer.analyze(item)
        assert isinstance(doc, PlanDocument)
        assert doc.title == "Fix login bug"

    def test_analyze_generates_steps(self, analyzer, tmp_path):
        item = PlanItem(
            source_path=tmp_path / "task.md",
            title="Weekly tasks",
            content="- Review emails\n- Send report\n- Update CRM",
        )
        doc = analyzer.analyze(item)
        assert len(doc.steps) >= 1

    def test_analyze_extracts_goal_from_prefix(self, analyzer, tmp_path):
        item = PlanItem(
            source_path=tmp_path / "g.md",
            title="Project",
            content="Goal: Launch new feature by Friday\nSteps follow.",
        )
        doc = analyzer.analyze(item)
        assert "Launch new feature" in doc.goal

    def test_analyze_fallback_title_from_filename(self, analyzer, tmp_path):
        item = PlanItem(
            source_path=tmp_path / "send-weekly-report.md",
            title="",
            content="Some content",
        )
        doc = analyzer.analyze(item)
        assert doc.title != ""

    def test_analyze_action_lines_become_steps(self, analyzer, tmp_path):
        item = PlanItem(
            source_path=tmp_path / "a.md",
            title="Tasks",
            content="review the codebase\nsend the email\nupdate the docs",
        )
        doc = analyzer.analyze(item)
        titles = [s.title.lower() for s in doc.steps]
        assert any("review" in t for t in titles)

    def test_context_truncated_at_500(self, analyzer, tmp_path):
        long_content = "word " * 200
        item = PlanItem(source_path=tmp_path / "long.md", title="Long", content=long_content)
        doc = analyzer.analyze(item)
        assert len(doc.context) <= 503  # 500 + "..."

    def test_analyze_tags_included(self, analyzer, tmp_path):
        item = PlanItem(
            source_path=tmp_path / "t.md",
            title="",
            content="Fix the #authentication #bug",
        )
        doc = analyzer.analyze(item)
        assert "authentication" in doc.tags or "bug" in doc.tags


# ---------------------------------------------------------------------------
# Writer tests
# ---------------------------------------------------------------------------

class TestPlanWriter:
    def test_write_creates_file(self, writer, tmp_vault):
        doc = PlanDocument(title="Test Plan", goal="Do something")
        path = writer.write(doc)
        assert path.exists()
        assert path.suffix == ".md"

    def test_write_goes_to_plans_dir(self, writer, tmp_vault):
        doc = PlanDocument(title="Plan in Plans Dir")
        path = writer.write(doc)
        assert path.parent == tmp_vault / "Plans"

    def test_write_file_contains_markdown(self, writer, tmp_vault):
        doc = PlanDocument(title="My Plan", goal="Achieve something")
        path = writer.write(doc)
        content = path.read_text(encoding="utf-8")
        assert "# My Plan" in content
        assert "PLAN-" in content

    def test_filename_includes_date(self, writer, tmp_vault):
        doc = PlanDocument(title="Date Test")
        path = writer.write(doc)
        # Filename should start with YYYY-MM-DD
        import re
        assert re.match(r"\d{4}-\d{2}-\d{2}-", path.name)

    def test_write_multiple_plans(self, writer, tmp_vault):
        for i in range(3):
            doc = PlanDocument(title=f"Plan {i}")
            path = writer.write(doc)
            assert path.exists()

    def test_move_to_done(self, writer, tmp_vault):
        src = tmp_vault / "Inbox" / "item.md"
        src.write_text("test", encoding="utf-8")
        done_path = writer.move_to_done(src)
        assert done_path is not None
        assert done_path.exists()
        assert not src.exists()

    def test_move_to_done_nonexistent_returns_none(self, writer, tmp_vault):
        result = writer.move_to_done(tmp_vault / "nonexistent.md")
        assert result is None

    def test_slugify_strips_special_chars(self, tmp_vault):
        w = PlanWriter(tmp_vault)
        slug = w._slugify("Hello, World! 123")
        assert "," not in slug
        assert "!" not in slug


# ---------------------------------------------------------------------------
# Logger tests
# ---------------------------------------------------------------------------

class TestPlanLogger:
    def test_info_creates_log_file(self, tmp_vault):
        logger = PlanLogger(tmp_vault)
        logger.info("Test message")
        log_files = list((tmp_vault / "70-LOGS" / "plan-loop").glob("*.jsonl"))
        assert len(log_files) == 1

    def test_log_entry_is_valid_json(self, tmp_vault):
        logger = PlanLogger(tmp_vault)
        logger.info("JSON test", {"key": "value"})
        log_file = list((tmp_vault / "70-LOGS" / "plan-loop").glob("*.jsonl"))[0]
        entry = json.loads(log_file.read_text().strip())
        assert entry["level"] == "INFO"
        assert entry["context"]["key"] == "value"

    def test_log_plan_created(self, tmp_vault):
        logger = PlanLogger(tmp_vault)
        logger.log_plan_created("PLAN-001", "Test", 3, "/vault/Plans/test.md")
        log_file = list((tmp_vault / "70-LOGS" / "plan-loop").glob("*.jsonl"))[0]
        content = log_file.read_text()
        assert "PLAN-001" in content

    def test_error_level(self, tmp_vault):
        logger = PlanLogger(tmp_vault)
        logger.error("Something failed")
        log_file = list((tmp_vault / "70-LOGS" / "plan-loop").glob("*.jsonl"))[0]
        content = log_file.read_text()
        assert "ERROR" in content


# ---------------------------------------------------------------------------
# PlanLoop integration tests
# ---------------------------------------------------------------------------

class TestPlanLoop:
    def test_empty_inbox_returns_zero(self, tmp_vault):
        loop = PlanLoop(tmp_vault)
        result = loop.run()
        assert result.items_found == 0
        assert result.plans_created == 0

    def test_inbox_item_creates_plan(self, tmp_vault):
        inbox = tmp_vault / "Inbox"
        (inbox / "task-001.md").write_text("# Fix login\nreview the auth code", encoding="utf-8")
        loop = PlanLoop(tmp_vault)
        result = loop.run()
        assert result.items_found == 1
        assert result.plans_created == 1

    def test_needs_action_item_processed(self, tmp_vault):
        na = tmp_vault / "Needs_Action"
        (na / "urgent-task.md").write_text("# Urgent\ncritical bug fix needed", encoding="utf-8")
        loop = PlanLoop(tmp_vault)
        result = loop.run()
        assert result.plans_created == 1

    def test_plan_file_written_to_plans_dir(self, tmp_vault):
        (tmp_vault / "Inbox" / "item.md").write_text("# Deploy\ndeploy to production", encoding="utf-8")
        loop = PlanLoop(tmp_vault)
        loop.run()
        plans = list((tmp_vault / "Plans").glob("*.md"))
        assert len(plans) == 1

    def test_source_item_moved_to_done(self, tmp_vault):
        src = tmp_vault / "Inbox" / "move-me.md"
        src.write_text("# Move\nupdate the dashboard", encoding="utf-8")
        loop = PlanLoop(tmp_vault, move_to_done=True)
        loop.run()
        assert not src.exists()
        done_files = list((tmp_vault / "Done").iterdir())
        assert len(done_files) == 1

    def test_move_to_done_false_keeps_source(self, tmp_vault):
        src = tmp_vault / "Inbox" / "keep-me.md"
        src.write_text("# Keep\ndo not move", encoding="utf-8")
        loop = PlanLoop(tmp_vault, move_to_done=False)
        loop.run()
        assert src.exists()

    def test_multiple_items_processed(self, tmp_vault):
        inbox = tmp_vault / "Inbox"
        for i in range(5):
            (inbox / f"task-{i}.md").write_text(f"# Task {i}\ndo task {i}", encoding="utf-8")
        loop = PlanLoop(tmp_vault)
        result = loop.run()
        assert result.plans_created == 5

    def test_unreadable_item_counted_as_error(self, tmp_vault, monkeypatch):
        (tmp_vault / "Inbox" / "bad.md").write_text("# Bad", encoding="utf-8")

        def _bad_parse(self, path):
            raise PermissionError("no permission")

        monkeypatch.setattr(PlanLoop, "_parse_item", _bad_parse)
        loop = PlanLoop(tmp_vault)
        result = loop.run()
        assert result.errors >= 1

    def test_scan_only_does_not_create_plans(self, tmp_vault):
        (tmp_vault / "Inbox" / "scan.md").write_text("# Scan me", encoding="utf-8")
        loop = PlanLoop(tmp_vault)
        items = loop.scan_only()
        assert len(items) == 1
        plans = list((tmp_vault / "Plans").glob("*.md"))
        assert len(plans) == 0

    def test_result_contains_plan_objects(self, tmp_vault):
        (tmp_vault / "Inbox" / "item.md").write_text("# Review\nreview the code", encoding="utf-8")
        loop = PlanLoop(tmp_vault)
        result = loop.run()
        assert len(result.plans) == 1
        assert isinstance(result.plans[0], PlanDocument)

    def test_txt_files_processed(self, tmp_vault):
        (tmp_vault / "Inbox" / "note.txt").write_text("send the invoice to client", encoding="utf-8")
        loop = PlanLoop(tmp_vault)
        result = loop.run()
        assert result.plans_created == 1

    def test_non_md_txt_files_ignored(self, tmp_vault):
        (tmp_vault / "Inbox" / "image.png").write_bytes(b"\x89PNG")
        loop = PlanLoop(tmp_vault)
        result = loop.run()
        assert result.items_found == 0

    def test_missing_inbox_dir_handled(self, tmp_path):
        # Vault without Inbox dir — should not crash
        (tmp_path / "Plans").mkdir()
        (tmp_path / "Done").mkdir()
        loop = PlanLoop(tmp_path)
        result = loop.run()
        assert result.items_found == 0

    def test_error_details_populated_on_failure(self, tmp_vault, monkeypatch):
        (tmp_vault / "Inbox" / "fail.md").write_text("# Fail", encoding="utf-8")

        original_analyze = PlanAnalyzer.analyze

        def _bad_analyze(self, item):
            raise ValueError("analysis failed")

        monkeypatch.setattr(PlanAnalyzer, "analyze", _bad_analyze)
        loop = PlanLoop(tmp_vault)
        result = loop.run()
        assert result.errors == 1
        assert len(result.error_details) == 1
        assert "fail.md" in result.error_details[0]
