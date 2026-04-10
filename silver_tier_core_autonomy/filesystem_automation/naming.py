"""
FILESYSTEM_AUTOMATION_SKILL — Naming Convention Parser & Validator
Phase 1: Enforce vault naming standards from NAMING-CONVENTIONS.md.

Patterns derived from obsidian-vault/NAMING-CONVENTIONS.md v1.0.0.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Pattern registry (derived from NAMING-CONVENTIONS.md)
# ---------------------------------------------------------------------------

# Prefix → target subfolder mapping
PREFIX_FOLDER_MAP: dict[str, str] = {
    "WF":   "20-PROCESSES/workflows",
    "SOP":  "20-PROCESSES/sops",
    "HITL": "20-PROCESSES/hitl-gates",
    "PB":   "20-PROCESSES/playbooks",
    "MCP":  "30-INTEGRATIONS/mcp-servers",
    "API":  "30-INTEGRATIONS/apis",
    "WH":   "30-INTEGRATIONS/webhooks",
    "TPL":  "60-PROMPTS/templates",
    "CHN":  "60-PROMPTS/chains",
    "EX":   "60-PROMPTS/examples",
    "EP":   "80-MEMORY/episodic",
    "SM":   "80-MEMORY/semantic",
    "PR":   "80-MEMORY/procedural",
    "CTX":  "80-MEMORY/context",
    "POL":  "40-SECURITY/policies",
    "ROLE": "40-SECURITY/roles",
    "AUDIT":"40-SECURITY/audits",
    "COMP": "40-SECURITY/compliance",
    "BM":   "50-BUSINESS/models",
    "AN":   "50-BUSINESS/analytics",
    "BR":   "50-BUSINESS/rules",
    "RPT":  "50-BUSINESS/reports",
}

# Compiled patterns  (name part only — no extension)
_RE_GENERAL   = re.compile(r"^\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")            # 001-some-name
_RE_PREFIXED  = re.compile(r"^[A-Z]+-\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")    # WF-001-some-name
_RE_DAILY_LOG = re.compile(r"^\d{4}-\d{2}-\d{2}$")                          # 2026-02-16
_RE_EPISODIC  = re.compile(r"^EP-\d{8}-[a-z0-9]+(?:-[a-z0-9]+)*$")        # EP-20260216-event
_RE_SEMANTIC  = re.compile(r"^SM-\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")
_RE_AGENT_LOG = re.compile(r"^[a-z0-9-]+-\d{4}-\d{2}-\d{2}$")             # agent-name-2026-02-16
_RE_ERROR_LOG = re.compile(r"^ERROR-\d{8}-\d{6}(?:-[a-z0-9]+)*$")


@dataclass
class NamingResult:
    """Outcome of a naming validation check."""
    valid: bool
    stem: str           # filename without extension
    extension: str      # '.md'
    detected_prefix: Optional[str]  # e.g. 'WF', 'EP', None
    suggested_name: Optional[str]   # auto-corrected name if invalid
    violations: list[str]           # human-readable issues


class NamingConventionParser:
    """
    Validates and normalises file names against vault conventions.

    Usage::

        parser = NamingConventionParser()
        result = parser.validate("My Agent Profile.MD")
        if not result.valid:
            corrected = result.suggested_name
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, filename: str | Path) -> NamingResult:
        """
        Check *filename* against vault naming rules.

        Returns a NamingResult with violations and, where possible,
        a suggested corrected name.
        """
        p = Path(filename)
        stem = p.stem
        ext = p.suffix

        violations: list[str] = []
        suggested = None

        # 1. Extension must be exactly .md (case-sensitive — .MD is a violation)
        if ext != ".md":
            violations.append(f"Extension must be '.md', got '{ext}'")

        # 2. Detect prefix (e.g. WF-, EP-, MCP-)
        prefix = self._extract_prefix(stem)

        # 3. Validate stem pattern
        if not self._matches_any_pattern(stem):
            violations.append(
                f"'{stem}' does not match any valid naming pattern "
                "(e.g. NNN-name, PREFIX-NNN-name, YYYY-MM-DD)"
            )

        # 4. Check for forbidden characters
        if " " in stem:
            violations.append("Spaces are not allowed in file names")
        if "_" in stem:
            violations.append("Underscores are not allowed; use hyphens")
        if re.search(r"[A-Z]", stem) and prefix is None:
            violations.append(
                "Uppercase letters are not allowed in general file names "
                "(prefixed names like WF-NNN are OK)"
            )

        # 5. Length check
        full_name = p.name
        if len(full_name) > 50:
            violations.append(
                f"File name too long: {len(full_name)} chars (max 50)"
            )

        if violations:
            suggested = self._suggest(stem, ext)

        return NamingResult(
            valid=len(violations) == 0,
            stem=stem,
            extension=ext,
            detected_prefix=prefix,
            suggested_name=suggested,
            violations=violations,
        )

    def suggest_folder(self, filename: str | Path) -> Optional[str]:
        """
        Return the conventional subfolder path (relative to vault root)
        for the given filename, or None if it cannot be determined.
        """
        stem = Path(filename).stem
        prefix = self._extract_prefix(stem)
        if prefix and prefix in PREFIX_FOLDER_MAP:
            return PREFIX_FOLDER_MAP[prefix]

        # Daily log pattern
        if _RE_DAILY_LOG.match(stem):
            return "70-LOGS/daily"

        # Agent log pattern
        if _RE_AGENT_LOG.match(stem):
            return "70-LOGS/agents"

        # Error log pattern
        if _RE_ERROR_LOG.match(stem):
            return "70-LOGS/errors"

        return None

    def next_id(self, folder: Path, width: int = 3) -> str:
        """
        Compute the next available sequence number for files in *folder*.

        Scans existing markdown files for leading NNN- sequences and
        returns the next integer as a zero-padded string.
        """
        max_id = 0
        if folder.is_dir():
            for f in folder.glob("*.md"):
                m = re.match(r"^(\d+)-", f.stem)
                if m:
                    max_id = max(max_id, int(m.group(1)))
        return str(max_id + 1).zfill(width)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_prefix(self, stem: str) -> Optional[str]:
        """Return the uppercase prefix (e.g. 'WF') or None."""
        m = re.match(r"^([A-Z]+)-", stem)
        if m and m.group(1) in PREFIX_FOLDER_MAP:
            return m.group(1)
        return None

    def _matches_any_pattern(self, stem: str) -> bool:
        return any(
            p.match(stem)
            for p in (
                _RE_GENERAL,
                _RE_PREFIXED,
                _RE_DAILY_LOG,
                _RE_EPISODIC,
                _RE_SEMANTIC,
                _RE_AGENT_LOG,
                _RE_ERROR_LOG,
            )
        )

    def _suggest(self, stem: str, ext: str) -> str:
        """
        Produce a best-effort corrected filename from a bad stem+ext.
        Strategy: lowercase, replace spaces/underscores with hyphens,
        strip special chars, prepend '001-' if no pattern matches.
        """
        clean = stem.lower()
        clean = re.sub(r"[\s_]+", "-", clean)           # spaces/underscores → hyphens
        clean = re.sub(r"[^a-z0-9\-]", "", clean)       # strip non-slug chars
        clean = re.sub(r"-{2,}", "-", clean).strip("-")  # collapse multiple hyphens

        # If still no leading NNN-, prepend placeholder
        if not re.match(r"^\d{3}-", clean) and not re.match(r"^[A-Z]+-", clean):
            clean = f"001-{clean}"

        return f"{clean}.md"
