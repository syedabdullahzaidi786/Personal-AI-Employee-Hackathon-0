"""Silver Tier — Plan.md Reasoning Loop.

Reads items from the vault Inbox / Needs_Action folders,
produces structured Plan.md files in the vault Plans/ folder,
and moves processed items to Done/.

Constitution compliance:
  - Principle II:  Explicit Over Implicit  (every decision logged)
  - Principle IV:  Composability           (atomic skill, single responsibility)
  - Principle V:   Memory as Knowledge     (plans persist to vault)
"""

from .loop import PlanLoop
from .models import PlanItem, PlanDocument, PlanStep

__all__ = ["PlanLoop", "PlanItem", "PlanDocument", "PlanStep"]
