"""
RALPH_WIGGUM_LOOP_SKILL — Memory Consolidator
Reads episodic memory entries from 80-MEMORY/episodic/ and produces
semantic summaries in 80-MEMORY/semantic/.

Constitution compliance:
  - Principle V:  Memory as Knowledge  (episodic → semantic consolidation)
  - Principle VI: Fail Safe  (never raises on read/write failure)

Phase 1 scope: simple, file-based consolidation — each episodic entry
is catalogued into a per-day semantic summary. No AI inference needed.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class MemoryConsolidator:
    """
    Scans episodic memory and writes daily semantic summaries.

    Episodic entries are any `.md` files in `80-MEMORY/episodic/`.
    Semantic summaries are written to `80-MEMORY/semantic/YYYY-MM-DD-summary.md`.

    Each tick the consolidator:
      1. Reads episodic entries modified today (or since last run).
      2. Appends them to the day's semantic summary (deduplicated by file path).
      3. Returns a dict with summary of what was consolidated.
    """

    _EPISODIC_DIR  = Path("80-MEMORY") / "episodic"
    _SEMANTIC_DIR  = Path("80-MEMORY") / "semantic"
    _PROCEDURAL_DIR = Path("80-MEMORY") / "procedural"

    def __init__(self, vault_root: str | Path) -> None:
        self._vault    = Path(vault_root)
        self._episodic = self._vault / self._EPISODIC_DIR
        self._semantic = self._vault / self._SEMANTIC_DIR
        for d in (self._episodic, self._semantic, self._vault / self._PROCEDURAL_DIR):
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def consolidate(self, since: Optional[datetime] = None) -> dict:
        """
        Consolidate episodic entries into the today's semantic summary.

        Parameters
        ----------
        since:
            Only consolidate entries modified after this datetime.
            If ``None``, consolidates entries modified today.

        Returns
        -------
        dict with keys: consolidated_count, skipped_count, summary_path
        """
        now = datetime.now(tz=timezone.utc)
        if since is None:
            # Default: entries modified today
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            since = today_start

        entries = self._collect_episodic(since)
        summary_path = self._semantic / f"{now.strftime('%Y-%m-%d')}-summary.md"

        consolidated = 0
        skipped      = 0

        existing_refs = self._load_existing_refs(summary_path)

        new_lines: list[str] = []
        for entry_path in entries:
            rel = str(entry_path.relative_to(self._vault))
            if rel in existing_refs:
                skipped += 1
                continue
            try:
                snippet = self._extract_snippet(entry_path)
            except Exception as exc:  # noqa: BLE001
                print(f"[MemoryConsolidator] read failed {entry_path}: {exc}", file=sys.stderr)
                skipped += 1
                continue
            new_lines.append(f"\n### {entry_path.stem}\n")
            new_lines.append(f"Source: `{rel}`\n")
            new_lines.append(f"{snippet}\n")
            consolidated += 1

        if new_lines:
            self._append_to_summary(summary_path, now, new_lines)

        return {
            "consolidated_count": consolidated,
            "skipped_count":      skipped,
            "summary_path":       str(summary_path.relative_to(self._vault)),
            "checked_at":         now.isoformat(),
        }

    def get_episodic_count(self) -> int:
        """Return number of episodic memory files."""
        if not self._episodic.exists():
            return 0
        return len(list(self._episodic.glob("*.md")))

    def get_semantic_count(self) -> int:
        """Return number of semantic summary files."""
        if not self._semantic.exists():
            return 0
        return len(list(self._semantic.glob("*.md")))

    def write_episodic(self, title: str, content: str, tags: Optional[list[str]] = None) -> Path:
        """
        Write a new episodic memory entry.

        Returns the path of the created file.
        """
        now = datetime.now(tz=timezone.utc)
        slug = title.lower().replace(" ", "-")[:40]
        filename = f"EP-{now.strftime('%Y%m%d')}-{slug}.md"
        path = self._episodic / filename

        frontmatter = (
            f"---\n"
            f"title: \"{title}\"\n"
            f"date: {now.strftime('%Y-%m-%d')}\n"
            f"type: episodic\n"
            f"tags: {tags or []}\n"
            f"---\n\n"
        )
        try:
            path.write_text(frontmatter + content + "\n", encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            print(f"[MemoryConsolidator] write failed {path}: {exc}", file=sys.stderr)
        return path

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _collect_episodic(self, since: datetime) -> list[Path]:
        """Return episodic .md files modified after *since* (UTC)."""
        if not self._episodic.exists():
            return []
        results = []
        for f in sorted(self._episodic.glob("*.md")):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                if mtime >= since:
                    results.append(f)
            except Exception:  # noqa: BLE001
                pass
        return results

    def _extract_snippet(self, path: Path, max_chars: int = 300) -> str:
        """Read the first non-frontmatter text from a file."""
        text = path.read_text(encoding="utf-8")
        # Strip YAML frontmatter
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                text = text[end + 3:].lstrip()
        snippet = text[:max_chars].strip()
        if len(text) > max_chars:
            snippet += "…"
        return snippet or "(empty)"

    def _load_existing_refs(self, summary_path: Path) -> set[str]:
        """Return set of source paths already in the summary."""
        if not summary_path.exists():
            return set()
        refs = set()
        for line in summary_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("Source: `") and line.endswith("`"):
                refs.add(line[9:-1])
        return refs

    def _append_to_summary(self, path: Path, now: datetime, lines: list[str]) -> None:
        """Append new entries to the semantic summary file."""
        try:
            if not path.exists():
                header = (
                    f"# Semantic Summary — {now.strftime('%Y-%m-%d')}\n\n"
                    f"Generated by RALPH_WIGGUM_LOOP_SKILL\n\n"
                    f"---\n"
                )
                path.write_text(header, encoding="utf-8")
            with path.open("a", encoding="utf-8") as fh:
                fh.write("".join(lines))
        except Exception as exc:  # noqa: BLE001
            print(f"[MemoryConsolidator] append failed {path}: {exc}", file=sys.stderr)
