"""Root pytest configuration — adds project root to sys.path.

Replaces the per-test sys.path.insert bootstrap with a single clean anchor
so all tier packages (bronze_tier_governance, silver_tier_core_autonomy, etc.)
are importable without manual path manipulation in test files.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
