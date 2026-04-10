"""
LinkedIn Watcher — Data Models.

Constitution compliance:
  - Principle II: Explicit Over Implicit
  - Section 9: Skill Anatomy
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LinkedInEventType(str, Enum):
    NEW_MESSAGE          = "new_message"
    CONNECTION_REQUEST   = "connection_request"
    POST_MENTION         = "post_mention"
    COMMENT_ON_POST      = "comment_on_post"
    PROFILE_VIEW         = "profile_view"
    NEW_NOTIFICATION     = "new_notification"


@dataclass
class LinkedInConfig:
    """Configuration for the LinkedIn Watcher."""
    watcher_id: str = "linkedin-watcher"
    vault_root: str = "."
    poll_interval_secs: float = 300.0    # 5 minutes (respect rate limits)
    tier: int = 1
    profile_url: str = ""                # LinkedIn profile URL (optional)
    max_results: int = 20                # Max events per poll
    event_types: list[LinkedInEventType] = field(
        default_factory=lambda: [
            LinkedInEventType.NEW_MESSAGE,
            LinkedInEventType.CONNECTION_REQUEST,
            LinkedInEventType.POST_MENTION,
        ]
    )


@dataclass
class LinkedInActivity:
    """A single activity item from LinkedIn."""
    activity_id: str
    event_type: LinkedInEventType
    sender_name: str = ""
    sender_profile: str = ""
    content: str = ""
    timestamp: str = ""
    url: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "activity_id":    self.activity_id,
            "event_type":     self.event_type.value,
            "sender_name":    self.sender_name,
            "sender_profile": self.sender_profile,
            "content":        self.content[:500] if self.content else "",
            "timestamp":      self.timestamp,
            "url":            self.url,
            "metadata":       self.metadata,
        }
