"""Golden Tier — LinkedIn Post Action.

Automatically posts business content to LinkedIn to generate sales leads.
Requires HITL Tier 2 approval before publishing.

Constitution compliance:
  - Principle III: HITL by Default (Tier 2 — external write action)
  - Principle IV:  Composability   (atomic skill, single purpose)
  - Section 6:     MCP Action Control (rate limits, audit logging)
"""

from .poster import LinkedInPoster
from .models import LinkedInPost, PostResult, PostStatus

__all__ = ["LinkedInPoster", "LinkedInPost", "PostResult", "PostStatus"]
