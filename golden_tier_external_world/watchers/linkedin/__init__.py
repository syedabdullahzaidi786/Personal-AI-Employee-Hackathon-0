"""Golden Tier — LinkedIn Watcher.

Monitors LinkedIn activity (mentions, messages, connection requests)
and triggers AI Employee actions.

Constitution compliance:
  - Section 9: Extends BaseWatcher pattern — atomic, composable, testable
  - Principle III: HITL by Default — post actions require Tier 2 approval
  - Principle VI: Fail Safe — tick() never raises
"""

from .watcher import LinkedInWatcher
from .models import LinkedInConfig, LinkedInEventType
from .client import MockLinkedInClient

__all__ = ["LinkedInWatcher", "LinkedInConfig", "LinkedInEventType", "MockLinkedInClient"]
