"""
SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL — Vault Guard
Scans Obsidian vault files for accidentally committed secrets.

Constitution compliance:
  - Section 8: "Prohibited Storage — plaintext in vault markdown files"
  - Principle VI: Fail Safe — scan errors skip the file, never crash the scan
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

from .models import ScanFinding, ScanSeverity


# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------
# Each entry: (pattern_name, severity, compiled_regex)
_PATTERNS: list[tuple[str, ScanSeverity, re.Pattern]] = [
    # AWS
    ("aws_access_key_id",
     ScanSeverity.CRITICAL,
     re.compile(r"\bAKIA[0-9A-Z]{16}\b")),

    ("aws_secret_access_key",
     ScanSeverity.CRITICAL,
     re.compile(r"(?i)aws[_\-]?secret[_\-]?access[_\-]?key\s*[=:]\s*[A-Za-z0-9/+=]{40}")),

    # GitHub
    ("github_token",
     ScanSeverity.CRITICAL,
     re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),

    # Generic bearer / JWT
    ("bearer_jwt",
     ScanSeverity.HIGH,
     re.compile(r"\bey[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b")),

    # Slack
    ("slack_token",
     ScanSeverity.CRITICAL,
     re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]+")),

    # Generic "password = " / "secret = " assignments
    ("password_assignment",
     ScanSeverity.HIGH,
     re.compile(r'(?i)(?:password|passwd)\s*[=:]\s*["\']?[^\s"\'<>{}\[\]\n]{8,}["\']?')),

    ("secret_assignment",
     ScanSeverity.HIGH,
     re.compile(r'(?i)(?:secret|api_?key|apikey|token)\s*[=:]\s*["\']?[A-Za-z0-9_\-+/=.]{16,}["\']?')),

    # Private key header
    ("private_key_pem",
     ScanSeverity.CRITICAL,
     re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),

    # Generic long hex (32+ chars) — lower confidence
    ("generic_hex_secret",
     ScanSeverity.MEDIUM,
     re.compile(r"\b[0-9a-fA-F]{40,64}\b")),
]

# Files / directories to always skip
_SKIP_DIRS = {".git", ".obsidian", ".claude", ".specify", "__pycache__", "node_modules"}
_SKIP_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".zip", ".tar", ".gz", ".bin"}

# Maximum file size to scan (avoid huge binary files)
_MAX_FILE_BYTES = 512 * 1024  # 512 KB


def _redact_match(text: str, match: re.Match) -> str:  # type: ignore[type-arg]
    """Replace secret chars in the matched substring with ***."""
    start, end = match.start(), match.end()
    secret_len = end - start
    visible    = min(4, secret_len // 4)
    return text[start: start + visible] + "***"


class VaultGuard:
    """
    Scans vault markdown and text files for accidental secret exposure.

    Usage::

        guard = VaultGuard("/path/to/obsidian-vault")
        findings = guard.scan()
        for f in findings:
            print(f.severity.value, f.file_path, f.line_number, f.redacted_match)
    """

    def __init__(
        self,
        vault_root: str | Path,
        extra_patterns: Optional[list[tuple[str, ScanSeverity, re.Pattern]]] = None,
    ) -> None:
        self._vault    = Path(vault_root)
        self._patterns = list(_PATTERNS) + (extra_patterns or [])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(
        self,
        path: Optional[str | Path] = None,
        min_severity: ScanSeverity = ScanSeverity.MEDIUM,
    ) -> list[ScanFinding]:
        """
        Scan the vault (or a specific subtree/file) for secrets.

        Parameters
        ----------
        path:
            Relative path within vault to scan. Defaults to full vault.
        min_severity:
            Only return findings at or above this severity level.

        Returns
        -------
        List of :class:`ScanFinding` objects, sorted by severity then file.
        """
        root = self._vault / path if path else self._vault
        findings: list[ScanFinding] = []

        if root.is_file():
            findings.extend(self._scan_file(root, min_severity))
        else:
            for file_path in self._iter_files(root):
                try:
                    findings.extend(self._scan_file(file_path, min_severity))
                except Exception as exc:  # noqa: BLE001
                    print(f"[VaultGuard] scan error {file_path}: {exc}", file=sys.stderr)

        findings.sort(key=lambda f: (self._severity_rank(f.severity), str(f.file_path)))
        return findings

    def scan_string(
        self,
        text: str,
        source_label: str = "<string>",
        min_severity: ScanSeverity = ScanSeverity.MEDIUM,
    ) -> list[ScanFinding]:
        """Scan an in-memory string for secrets (useful for pre-write validation)."""
        return self._scan_lines(text.splitlines(), source_label, min_severity)

    def is_safe_to_write(self, content: str) -> tuple[bool, list[ScanFinding]]:
        """Return (True, []) if content has no CRITICAL/HIGH secrets."""
        findings = self.scan_string(content, min_severity=ScanSeverity.HIGH)
        return len(findings) == 0, findings

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _iter_files(self, root: Path):
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() in _SKIP_EXTS:
                continue
            try:
                if path.stat().st_size > _MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield path

    def _scan_file(self, file_path: Path, min_severity: ScanSeverity) -> list[ScanFinding]:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            print(f"[VaultGuard] read error {file_path}: {exc}", file=sys.stderr)
            return []

        try:
            rel_path = str(file_path.relative_to(self._vault))
        except ValueError:
            rel_path = str(file_path)

        return self._scan_lines(text.splitlines(), rel_path, min_severity)

    def _scan_lines(
        self,
        lines: list[str],
        source: str,
        min_severity: ScanSeverity,
    ) -> list[ScanFinding]:
        findings: list[ScanFinding] = []
        min_rank = self._severity_rank(min_severity)

        for lineno, line in enumerate(lines, start=1):
            for pattern_name, severity, regex in self._patterns:
                if self._severity_rank(severity) > min_rank:
                    continue
                for match in regex.finditer(line):
                    redacted = _redact_match(line, match)
                    # Redact the full line context too
                    context = line[:match.start()] + "[REDACTED]" + line[match.end():]
                    findings.append(ScanFinding(
                        file_path=source,
                        line_number=lineno,
                        pattern_name=pattern_name,
                        severity=severity,
                        redacted_match=redacted,
                        context=context[:200],
                    ))
        return findings

    @staticmethod
    def _severity_rank(s: ScanSeverity) -> int:
        return {"critical": 0, "high": 1, "medium": 2, "info": 3}[s.value]
