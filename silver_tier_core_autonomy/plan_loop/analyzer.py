"""
Plan Loop — Analyzer.

Parses inbox items and generates structured PlanDocuments.
Uses rule-based reasoning (no external AI call needed — Claude Code
already drives the outer loop; this module does structured extraction).

Constitution compliance:
  - Principle II: Explicit Over Implicit (all reasoning steps declared)
  - Principle I:  Local-First (no cloud API calls)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import PlanDocument, PlanItem, PlanStep, StepPriority


# ---------------------------------------------------------------------------
# Keyword → priority mapping
# ---------------------------------------------------------------------------

_URGENT_KEYWORDS = {"urgent", "asap", "critical", "immediately", "emergency", "blocker"}
_LOW_KEYWORDS    = {"someday", "optional", "nice-to-have", "low", "future", "later"}


def _infer_priority(text: str) -> StepPriority:
    lower = text.lower()
    if any(k in lower for k in _URGENT_KEYWORDS):
        return StepPriority.HIGH
    if any(k in lower for k in _LOW_KEYWORDS):
        return StepPriority.LOW
    return StepPriority.MEDIUM


# ---------------------------------------------------------------------------
# Tag extractor
# ---------------------------------------------------------------------------

def _extract_tags(content: str, title: str) -> list[str]:
    """Extract #hashtags and keywords from content."""
    tags = re.findall(r"#(\w+)", content + " " + title)
    tags = [t.lower() for t in tags]
    tags.append("plan")
    tags.append("ai-generated")
    return list(dict.fromkeys(tags))  # deduplicate, preserve order


# ---------------------------------------------------------------------------
# Step generator
# ---------------------------------------------------------------------------

_ACTION_VERBS = [
    "review", "send", "write", "create", "update", "check", "schedule",
    "call", "email", "follow up", "research", "analyze", "draft", "fix",
    "deploy", "test", "verify", "confirm", "notify", "post",
]


def _extract_action_lines(content: str) -> list[str]:
    """Find lines that look like action items."""
    actions = []
    lines = content.splitlines()
    for line in lines:
        stripped = line.strip().lstrip("-*•· 0123456789.")
        if not stripped:
            continue
        lower = stripped.lower()
        if any(lower.startswith(v) for v in _ACTION_VERBS):
            actions.append(stripped)
        elif re.match(r"^\[[ x]\]", stripped):  # checkbox
            actions.append(re.sub(r"^\[[ x]\]\s*", "", stripped))
    return actions


def _generate_steps(title: str, content: str, goal: str) -> list[PlanStep]:
    """Generate PlanSteps from content analysis."""
    action_lines = _extract_action_lines(content)
    steps: list[PlanStep] = []

    # If explicit action items found, use them
    if action_lines:
        for i, action in enumerate(action_lines[:8], start=1):  # max 8 steps
            steps.append(PlanStep(
                id=str(i),
                title=action[:80],  # cap at 80 chars
                description=action,
                priority=_infer_priority(action),
                estimated_minutes=30,
                depends_on=[str(i - 1)] if i > 1 else [],
            ))
        return steps

    # Fallback: generate generic steps from the goal
    generic = [
        ("1", f"Understand and clarify: {title[:60]}", 15),
        ("2", "Gather required information and resources", 30),
        ("3", "Draft initial approach / solution", 45),
        ("4", "Review and validate approach", 20),
        ("5", "Execute and document outcome", 60),
    ]
    for sid, stitle, mins in generic:
        steps.append(PlanStep(
            id=sid,
            title=stitle,
            estimated_minutes=mins,
            depends_on=[str(int(sid) - 1)] if int(sid) > 1 else [],
        ))
    return steps


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class PlanAnalyzer:
    """
    Converts a PlanItem (inbox entry) into a PlanDocument.

    All reasoning is local and deterministic — no external calls.
    """

    def analyze(self, item: PlanItem) -> PlanDocument:
        """
        Analyze *item* and return a fully populated PlanDocument.
        """
        title = item.title or item.source_path.stem.replace("-", " ").replace("_", " ").title()
        tags  = _extract_tags(item.content, title)
        goal  = self._extract_goal(item.content, title)
        steps = _generate_steps(title, item.content, goal)

        return PlanDocument(
            title=title,
            source_item=item,
            steps=steps,
            context=self._extract_context(item.content),
            goal=goal,
            tags=tags,
            created_at=datetime.now(tz=timezone.utc),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_goal(self, content: str, title: str) -> str:
        """Try to find an explicit goal statement; fall back to title."""
        for line in content.splitlines():
            lower = line.lower().strip()
            if lower.startswith(("goal:", "objective:", "purpose:", "task:")):
                return line.split(":", 1)[-1].strip()
        # Use first non-empty sentence
        sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 10]
        if sentences:
            return sentences[0][:200]
        return f"Complete task: {title}"

    def _extract_context(self, content: str) -> str:
        """Return cleaned content as context (max 500 chars)."""
        cleaned = content.strip()
        if len(cleaned) > 500:
            return cleaned[:497] + "..."
        return cleaned
