"""
FILESYSTEM_AUTOMATION_SKILL — Safe File Operations
Phase 1: Atomic rename and move with backup/rollback.

Pattern: Try → Validate → Execute → Verify (TVEV)

Constitution compliance:
  - Principle II: Explicit Over Implicit
  - Principle VI: Fail Safe, Fail Visible
  - Section 9: Skill Design Rules (idempotent, fail-fast)
"""

import hashlib
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .logger import SkillLogger
from .validator import SecurityError, Validator, VaultError


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class OperationResult:
    """Outcome of a file operation."""
    success: bool
    source: Path
    destination: Optional[Path]
    operation: str          # 'rename' | 'move' | 'add_frontmatter'
    duration_ms: float
    message: str
    rolled_back: bool = False
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

def _build_frontmatter(
    file_id: str,
    name: str,
    doc_type: str,
    tags: list[str],
    created_iso: str,
    updated_iso: str,
) -> str:
    tag_list = ", ".join(tags)
    return (
        f"---\n"
        f"id: {file_id}\n"
        f"name: {name}\n"
        f"type: {doc_type}\n"
        f"status: draft\n"
        f"created: {created_iso}\n"
        f"updated: {updated_iso}\n"
        f"tags: [{tag_list}]\n"
        f"---\n"
    )


def _has_frontmatter(text: str) -> bool:
    return text.lstrip().startswith("---")


def _file_checksum(path: Path) -> str:
    """MD5 of file content — fast enough for integrity checks."""
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """
    Prevents cascade failures if the filesystem becomes unstable.

    States: CLOSED → OPEN (after threshold) → HALF_OPEN → CLOSED
    """

    def __init__(self, failure_threshold: int = 3, timeout_seconds: float = 300.0) -> None:
        self._threshold = failure_threshold
        self._timeout = timeout_seconds
        self._failures = 0
        self._opened_at: Optional[float] = None
        self._state = "CLOSED"

    @property
    def state(self) -> str:
        if self._state == "OPEN":
            if time.monotonic() - (self._opened_at or 0) >= self._timeout:
                self._state = "HALF_OPEN"
        return self._state

    def record_success(self) -> None:
        self._failures = 0
        self._state = "CLOSED"
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._state = "OPEN"
            self._opened_at = time.monotonic()

    def allow_request(self) -> bool:
        s = self.state
        return s in ("CLOSED", "HALF_OPEN")


# ---------------------------------------------------------------------------
# FileOperations
# ---------------------------------------------------------------------------

class FileOperations:
    """
    Atomic file rename and move operations with full audit trail.

    Every operation:
      1. Creates a temporary backup (.bak)
      2. Performs the operation
      3. Verifies content integrity (checksum)
      4. Logs the result
      5. Rolls back on any failure
    """

    BACKUP_SUFFIX = ".bak"

    def __init__(
        self,
        validator: Validator,
        logger: SkillLogger,
        circuit_breaker: Optional[CircuitBreaker] = None,
        dry_run: bool = False,
    ) -> None:
        self._validator = validator
        self._logger = logger
        self._cb = circuit_breaker or CircuitBreaker()
        self._dry_run = dry_run

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rename(self, source: str | Path, new_name: str) -> OperationResult:
        """
        Rename *source* to *new_name* within the same directory.

        *new_name* is a bare filename (no path separators).
        """
        src_path = Path(source)
        dst_path = src_path.parent / new_name
        return self._execute("rename", src_path, dst_path)

    def move(self, source: str | Path, destination: str | Path) -> OperationResult:
        """
        Move *source* to *destination* (which must include the filename).
        """
        return self._execute("move", Path(source), Path(destination))

    def add_frontmatter(
        self,
        path: str | Path,
        file_id: str,
        name: str,
        doc_type: str,
        tags: list[str],
        created_iso: str,
        updated_iso: str,
    ) -> OperationResult:
        """
        Prepend YAML frontmatter to *path* if not already present.
        Content is never modified — only the header is prepended.
        """
        t0 = time.monotonic()
        target = Path(path)

        if self._dry_run:
            return OperationResult(
                success=True,
                source=target,
                destination=target,
                operation="add_frontmatter",
                duration_ms=0.0,
                message=f"[DRY RUN] Would add frontmatter to {target.name}",
            )

        if not self._cb.allow_request():
            return self._blocked_result(target, "add_frontmatter")

        try:
            src, _ = self._validator.preflight(target)
            text = src.read_text(encoding="utf-8")

            if _has_frontmatter(text):
                return OperationResult(
                    success=True,
                    source=src,
                    destination=src,
                    operation="add_frontmatter",
                    duration_ms=self._ms(t0),
                    message=f"Frontmatter already present: {src.name}",
                )

            fm = _build_frontmatter(file_id, name, doc_type, tags, created_iso, updated_iso)
            backup = self._backup(src)
            try:
                src.write_text(fm + text, encoding="utf-8")
            except Exception:
                self._restore(backup, src)
                raise

            backup.unlink(missing_ok=True)
            self._cb.record_success()
            ms = self._ms(t0)
            self._logger.info(
                f"Added frontmatter to {src.name}",
                context={"duration_ms": round(ms)},
            )
            self._logger.audit(
                "add_frontmatter",
                {
                    "file": str(src),
                    "result": "success",
                    "duration_ms": round(ms),
                },
            )
            return OperationResult(
                success=True,
                source=src,
                destination=src,
                operation="add_frontmatter",
                duration_ms=ms,
                message=f"Added frontmatter to {src.name}",
            )

        except (SecurityError, VaultError, FileNotFoundError, PermissionError) as exc:
            self._cb.record_failure()
            self._logger.error(str(exc), context={"operation": "add_frontmatter"})
            return OperationResult(
                success=False,
                source=target,
                destination=None,
                operation="add_frontmatter",
                duration_ms=self._ms(t0),
                message=str(exc),
                error=type(exc).__name__,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute(self, op: str, src: Path, dst: Path) -> OperationResult:
        t0 = time.monotonic()

        if self._dry_run:
            return OperationResult(
                success=True,
                source=src,
                destination=dst,
                operation=op,
                duration_ms=0.0,
                message=f"[DRY RUN] Would {op}: {src.name} → {dst.name}",
            )

        if not self._cb.allow_request():
            return self._blocked_result(src, op, dst)

        backup: Optional[Path] = None
        try:
            src_resolved, dst_resolved = self._validator.preflight(src, dst)
            checksum_before = _file_checksum(src_resolved)

            backup = self._backup(src_resolved)
            shutil.move(str(src_resolved), str(dst_resolved))

            # Verify
            if not dst_resolved.exists():
                raise RuntimeError(f"{op} verification failed: {dst_resolved} not found")
            checksum_after = _file_checksum(dst_resolved)
            if checksum_before != checksum_after:
                self._restore(backup, src_resolved)
                raise RuntimeError(
                    f"Content integrity check failed after {op}; rolled back"
                )

            backup.unlink(missing_ok=True)
            self._cb.record_success()
            ms = self._ms(t0)
            self._logger.info(
                f"{op.capitalize()}: {src_resolved.name} → {dst_resolved.name}",
                context={"duration_ms": round(ms)},
            )
            self._logger.audit(
                op,
                {
                    "file_before": str(src_resolved),
                    "file_after": str(dst_resolved),
                    "checksum_before": checksum_before,
                    "checksum_after": checksum_after,
                    "result": "success",
                    "duration_ms": round(ms),
                },
            )
            return OperationResult(
                success=True,
                source=src_resolved,
                destination=dst_resolved,
                operation=op,
                duration_ms=ms,
                message=f"{op.capitalize()}: {src_resolved.name} → {dst_resolved.name}",
            )

        except (SecurityError, VaultError, FileNotFoundError, FileExistsError, PermissionError, RuntimeError) as exc:
            self._cb.record_failure()
            rolled_back = False
            if backup and backup.exists() and not src.exists():
                try:
                    self._restore(backup, src)
                    rolled_back = True
                except Exception:
                    pass
            self._logger.error(
                str(exc),
                context={"operation": op, "source": str(src)},
            )
            return OperationResult(
                success=False,
                source=src,
                destination=dst,
                operation=op,
                duration_ms=self._ms(t0),
                message=str(exc),
                rolled_back=rolled_back,
                error=type(exc).__name__,
            )

    def _backup(self, path: Path) -> Path:
        backup = path.with_suffix(path.suffix + self.BACKUP_SUFFIX)
        shutil.copy2(str(path), str(backup))
        return backup

    def _restore(self, backup: Path, original: Path) -> None:
        if backup.exists():
            shutil.move(str(backup), str(original))

    def _blocked_result(
        self,
        src: Path,
        op: str,
        dst: Optional[Path] = None,
    ) -> OperationResult:
        msg = f"Circuit breaker OPEN — operation '{op}' rejected (state: {self._cb.state})"
        self._logger.warn(msg)
        return OperationResult(
            success=False,
            source=src,
            destination=dst,
            operation=op,
            duration_ms=0.0,
            message=msg,
            error="CircuitBreakerOpen",
        )

    @staticmethod
    def _ms(t0: float) -> float:
        return (time.monotonic() - t0) * 1000
