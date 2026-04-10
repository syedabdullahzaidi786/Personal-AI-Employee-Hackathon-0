"""
Plan Loop — Plan Writer.

Writes PlanDocument objects as Plan.md files to the vault.
Moves processed source items to Done/.

Constitution compliance:
  - Principle I:  Local-First (vault is source of truth)
  - Principle VI: Fail Safe (atomic write with temp file)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from .models import PlanDocument


class PlanWriter:
    """
    Writes Plan.md files to vault/Plans/ and moves source items to Done/.

    Atomic write pattern: write to .tmp → rename → verify.
    """

    _PLANS_DIR = "Plans"
    _DONE_DIR  = "Done"

    def __init__(self, vault_root: str | Path) -> None:
        self._vault = Path(vault_root)
        self._plans_dir = self._vault / self._PLANS_DIR
        self._done_dir  = self._vault / self._DONE_DIR
        self._plans_dir.mkdir(parents=True, exist_ok=True)
        self._done_dir.mkdir(parents=True, exist_ok=True)

    def write(self, doc: PlanDocument) -> Path:
        """
        Write *doc* as a Plan.md file.

        Returns the path of the written file.
        Raises RuntimeError if the write fails.
        """
        filename  = self._make_filename(doc)
        dest_path = self._plans_dir / filename
        tmp_path  = dest_path.with_suffix(".tmp")

        markdown = doc.to_markdown()

        try:
            tmp_path.write_text(markdown, encoding="utf-8")
            tmp_path.rename(dest_path)
        except Exception as exc:
            tmp_path.unlink(missing_ok=True)
            raise RuntimeError(f"PlanWriter: failed to write {dest_path}: {exc}") from exc

        # Verify
        if not dest_path.exists():
            raise RuntimeError(f"PlanWriter: verification failed — {dest_path} not found after write")

        return dest_path

    def move_to_done(self, source_path: Path) -> Optional[Path]:
        """
        Move *source_path* to Done/ folder.

        Returns the new path, or None if source does not exist.
        """
        if not source_path.exists():
            return None

        dest = self._done_dir / source_path.name
        # Avoid overwriting existing Done item
        if dest.exists():
            stem = source_path.stem
            suffix = source_path.suffix
            dest = self._done_dir / f"{stem}-{int(time.time())}{suffix}"

        try:
            source_path.rename(dest)
        except Exception:
            # Non-fatal — just log (caller handles)
            return None

        return dest

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_filename(self, doc: PlanDocument) -> str:
        date_str = doc.created_at.strftime("%Y-%m-%d")
        slug = self._slugify(doc.title)[:40]
        return f"{date_str}-{slug}-{doc.plan_id.lower()}.md"

    @staticmethod
    def _slugify(text: str) -> str:
        import re
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        return text.strip("-")
