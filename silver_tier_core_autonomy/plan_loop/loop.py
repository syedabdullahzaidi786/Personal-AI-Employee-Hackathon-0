"""
Plan Loop — Main Reasoning Loop.

Scans vault Inbox + Needs_Action folders, creates Plan.md files,
and moves processed items to Done/.

Constitution compliance:
  - Principle II:  Explicit Over Implicit  (every decision logged)
  - Principle III: HITL by Default         (Tier 2 items require approval)
  - Principle IV:  Composability           (delegates to analyzer + writer)
  - Principle V:   Memory as Knowledge     (plans persist to vault)
  - Principle VI:  Fail Safe               (errors captured per item; loop continues)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .analyzer import PlanAnalyzer
from .logger import PlanLogger
from .models import PlanDocument, PlanItem
from .writer import PlanWriter


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class PlanLoopResult:
    """Summary of one PlanLoop.run() execution."""
    items_found: int = 0
    plans_created: int = 0
    errors: int = 0
    plans: list[PlanDocument] = field(default_factory=list)
    error_details: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# PlanLoop
# ---------------------------------------------------------------------------

class PlanLoop:
    """
    Scans vault inbox folders and generates Plan.md files.

    Watched folders (relative to vault_root):
      - ``Inbox/``
      - ``Needs_Action/``

    For each .md or .txt item found:
      1. Parse into a PlanItem
      2. Analyze → PlanDocument
      3. Write Plan.md to Plans/
      4. Move source item to Done/

    Usage::

        loop = PlanLoop(vault_root="/path/to/obsidian-vault")
        result = loop.run()
        print(f"{result.plans_created} plans created")
    """

    _INBOX_DIRS = ["Inbox", "Needs_Action"]
    _ITEM_SUFFIXES = {".md", ".txt"}

    def __init__(
        self,
        vault_root: str | Path,
        move_to_done: bool = True,
    ) -> None:
        self._vault       = Path(vault_root)
        self._move_done   = move_to_done
        self._analyzer    = PlanAnalyzer()
        self._writer      = PlanWriter(vault_root)
        self._logger      = PlanLogger(vault_root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> PlanLoopResult:
        """
        Execute one full scan of inbox folders.

        Returns a :class:`PlanLoopResult` — never raises.
        """
        result = PlanLoopResult()
        raw    = self._collect_items()
        items  = [i for i in raw if i is not None]
        result.items_found = len(raw)
        result.errors     += raw.count(None)  # count collection failures

        self._logger.info(f"Plan loop started — {len(raw)} item(s) found, {len(items)} readable")

        for item in items:
            try:
                doc  = self._analyzer.analyze(item)
                path = self._writer.write(doc)
                result.plans.append(doc)
                result.plans_created += 1

                self._logger.log_plan_created(
                    doc.plan_id, doc.title, len(doc.steps), str(path)
                )
                self._logger.log_item_processed(str(item.source_path), doc.plan_id)

                if self._move_done:
                    self._writer.move_to_done(item.source_path)

            except Exception as exc:  # noqa: BLE001
                result.errors += 1
                result.error_details.append(f"{item.source_path.name}: {exc}")
                self._logger.error(
                    f"Failed to process {item.source_path.name}: {exc}",
                    {"source": str(item.source_path)},
                )

        self._logger.log_loop_run(result.items_found, result.plans_created, result.errors)
        return result

    def scan_only(self) -> list[PlanItem]:
        """
        Return inbox items without processing them (dry-run discovery).
        """
        return self._collect_items()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _collect_items(self) -> list[Optional[PlanItem]]:
        """Return list of PlanItems (None entries represent parse failures)."""
        items: list[Optional[PlanItem]] = []
        for dir_name in self._INBOX_DIRS:
            folder = self._vault / dir_name
            if not folder.exists():
                continue
            for path in sorted(folder.iterdir()):
                if path.suffix.lower() in self._ITEM_SUFFIXES and path.is_file():
                    try:
                        item = self._parse_item(path)
                        items.append(item)  # None if unreadable
                    except Exception as exc:  # noqa: BLE001
                        self._logger.error(f"Cannot collect {path.name}: {exc}")
                        items.append(None)
        return items

    def _parse_item(self, path: Path) -> Optional[PlanItem]:
        """Read a file and return a PlanItem, or None on read error."""
        try:
            content = path.read_text(encoding="utf-8")
            title   = self._extract_title(path, content)
            return PlanItem(
                source_path=path,
                title=title,
                content=content,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.error(f"Cannot read {path.name}: {exc}")
            return None

    @staticmethod
    def _extract_title(path: Path, content: str) -> str:
        """Use first # heading, or filename stem as title."""
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return path.stem.replace("-", " ").replace("_", " ").title()
