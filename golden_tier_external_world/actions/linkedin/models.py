"""
LinkedIn Post Action — Data Models.

Constitution compliance:
  - Principle II: Explicit Over Implicit
  - Section 9: Skill Anatomy
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class PostStatus(str, Enum):
    DRAFT     = "draft"
    PENDING   = "pending_approval"   # Awaiting HITL Tier 2 approval
    APPROVED  = "approved"
    POSTED    = "posted"
    FAILED    = "failed"
    REJECTED  = "rejected"


class PostType(str, Enum):
    TEXT         = "text"
    TEXT_WITH_URL = "text_with_url"
    ARTICLE      = "article"


@dataclass
class LinkedInPost:
    """A LinkedIn post to be published."""
    post_id: str = field(default_factory=lambda: f"POST-{uuid.uuid4().hex[:8].upper()}")
    content: str = ""
    post_type: PostType = PostType.TEXT
    url: str = ""                    # Optional URL to include
    hashtags: list[str] = field(default_factory=list)
    status: PostStatus = PostStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    scheduled_for: Optional[datetime] = None

    def to_full_text(self) -> str:
        """Build the full post text with hashtags and URL."""
        parts = [self.content]
        if self.url:
            parts.append(f"\n{self.url}")
        if self.hashtags:
            tags = " ".join(f"#{t.lstrip('#')}" for t in self.hashtags)
            parts.append(f"\n\n{tags}")
        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "post_id":    self.post_id,
            "content":    self.content[:300] + "..." if len(self.content) > 300 else self.content,
            "post_type":  self.post_type.value,
            "hashtags":   self.hashtags,
            "status":     self.status.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PostResult:
    """Result of a post operation."""
    post_id: str
    status: PostStatus
    linkedin_post_id: Optional[str] = None   # LinkedIn's own ID after posting
    error: Optional[str] = None
    posted_at: Optional[datetime] = None
    url: Optional[str] = None                # URL of the live post

    def to_dict(self) -> dict:
        return {
            "post_id":          self.post_id,
            "status":           self.status.value,
            "linkedin_post_id": self.linkedin_post_id,
            "error":            self.error,
            "posted_at":        self.posted_at.isoformat() if self.posted_at else None,
            "url":              self.url,
        }
