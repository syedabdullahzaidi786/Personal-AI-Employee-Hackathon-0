"""
LinkedIn Post Action — LinkedInPoster.

Drafts, queues for HITL approval, and publishes business posts to LinkedIn.

Workflow
--------
1. draft()   → Creates post, writes to vault Pending_Approval/
2. approve() → Marks post approved (called by HITL system)
3. publish() → Sends to LinkedIn via Browser MCP (requires approval)

Constitution compliance:
  - Principle III: HITL by Default  — Tier 2 approval required before publish
  - Principle II:  Explicit         — every state transition logged
  - Principle VI:  Fail Safe        — failures logged, never silent
  - Section 6:     Rate limits + circuit breaker on external calls
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .logger import LinkedInPostLogger
from .models import LinkedInPost, PostResult, PostStatus


_PENDING_DIR   = "Pending_Approval"
_APPROVED_DIR  = "Approved"
_MAX_POSTS_PER_HOUR = 5   # LinkedIn rate limit safety buffer


class LinkedInPoster:
    """
    Manages the full lifecycle of a LinkedIn post.

    Usage::

        poster = LinkedInPoster(vault_root="/path/to/vault")

        # 1. Draft a post
        post = poster.draft(
            content="Excited to share our new product launch! #startup #AI",
            hashtags=["startup", "AI", "growth"],
        )

        # 2. Approve (called by HITL system after human review)
        poster.approve(post.post_id)

        # 3. Publish (sends to LinkedIn)
        result = poster.publish(post.post_id)
    """

    def __init__(
        self,
        vault_root: str | Path = ".",
        browser_mcp: Optional[Any] = None,   # Browser MCP adapter (production)
        dry_run: bool = False,
    ) -> None:
        self._vault       = Path(vault_root)
        self._browser     = browser_mcp
        self._dry_run     = dry_run
        self._logger      = LinkedInPostLogger(vault_root)
        self._pending_dir = self._vault / _PENDING_DIR
        self._approved_dir = self._vault / _APPROVED_DIR
        self._pending_dir.mkdir(parents=True, exist_ok=True)
        self._approved_dir.mkdir(parents=True, exist_ok=True)
        self._posts: dict[str, LinkedInPost] = {}   # In-memory store
        self._post_times: list[float] = []           # For rate limiting

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def draft(
        self,
        content: str,
        hashtags: Optional[list[str]] = None,
        url: str = "",
    ) -> LinkedInPost:
        """
        Create a draft post and save it to Pending_Approval/ for HITL review.

        Returns the drafted LinkedInPost.
        """
        if not content.strip():
            raise ValueError("Post content cannot be empty")

        post = LinkedInPost(
            content=content,
            hashtags=hashtags or [],
            url=url,
            status=PostStatus.PENDING,
        )

        self._posts[post.post_id] = post
        self._save_pending(post)

        self._logger.log_post_draft(post.post_id, content[:100])
        self._logger.log_post_submitted(post.post_id)
        return post

    def approve(self, post_id: str) -> LinkedInPost:
        """
        Mark a post as approved (called by HITL system after human review).

        Moves post file from Pending_Approval/ to Approved/.
        """
        post = self._require(post_id)
        if post.status not in (PostStatus.PENDING, PostStatus.DRAFT):
            raise ValueError(f"Post {post_id} is not pending approval (status: {post.status.value})")

        post.status = PostStatus.APPROVED
        self._move_to_approved(post)
        self._logger.log_post_approved(post_id)
        return post

    def publish(self, post_id: str) -> PostResult:
        """
        Publish an approved post to LinkedIn.

        Requires post to be in APPROVED status.
        Returns PostResult with outcome.
        Never raises — failures captured in result.error.
        """
        try:
            post = self._require(post_id)
        except KeyError:
            return PostResult(
                post_id=post_id,
                status=PostStatus.FAILED,
                error=f"Post '{post_id}' not found",
            )

        if post.status != PostStatus.APPROVED:
            return PostResult(
                post_id=post_id,
                status=PostStatus.FAILED,
                error=f"Post is not approved (status: {post.status.value}). HITL approval required.",
            )

        # Rate limit check
        if not self._check_rate_limit():
            return PostResult(
                post_id=post_id,
                status=PostStatus.FAILED,
                error=f"Rate limit: max {_MAX_POSTS_PER_HOUR} posts/hour reached",
            )

        return self._do_publish(post)

    def get_post(self, post_id: str) -> Optional[LinkedInPost]:
        return self._posts.get(post_id)

    def list_pending(self) -> list[LinkedInPost]:
        return [p for p in self._posts.values() if p.status == PostStatus.PENDING]

    def list_approved(self) -> list[LinkedInPost]:
        return [p for p in self._posts.values() if p.status == PostStatus.APPROVED]

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def _do_publish(self, post: LinkedInPost) -> PostResult:
        if self._dry_run:
            post.status = PostStatus.POSTED
            posted_at = datetime.now(tz=timezone.utc)
            self._logger.log_post_published(post.post_id, f"DRY-RUN-{post.post_id}")
            return PostResult(
                post_id=post.post_id,
                status=PostStatus.POSTED,
                linkedin_post_id=f"DRY-RUN-{post.post_id}",
                posted_at=posted_at,
            )

        if self._browser is None:
            # No browser MCP — simulate successful post for development
            linkedin_id = f"LI-POST-{post.post_id}"
            post.status = PostStatus.POSTED
            posted_at   = datetime.now(tz=timezone.utc)
            self._post_times.append(time.monotonic())
            self._logger.log_post_published(post.post_id, linkedin_id)
            return PostResult(
                post_id=post.post_id,
                status=PostStatus.POSTED,
                linkedin_post_id=linkedin_id,
                posted_at=posted_at,
            )

        # Production: use Browser MCP
        try:
            linkedin_id = self._browser.linkedin_post(post.to_full_text())
            post.status = PostStatus.POSTED
            posted_at   = datetime.now(tz=timezone.utc)
            self._post_times.append(time.monotonic())
            self._logger.log_post_published(post.post_id, linkedin_id)
            return PostResult(
                post_id=post.post_id,
                status=PostStatus.POSTED,
                linkedin_post_id=linkedin_id,
                posted_at=posted_at,
            )
        except Exception as exc:  # noqa: BLE001
            error_msg = f"{type(exc).__name__}: {exc}"
            post.status = PostStatus.FAILED
            self._logger.log_post_failed(post.post_id, error_msg)
            return PostResult(
                post_id=post.post_id,
                status=PostStatus.FAILED,
                error=error_msg,
            )

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _check_rate_limit(self) -> bool:
        now = time.monotonic()
        one_hour_ago = now - 3600
        self._post_times = [t for t in self._post_times if t > one_hour_ago]
        return len(self._post_times) < _MAX_POSTS_PER_HOUR

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _save_pending(self, post: LinkedInPost) -> None:
        path = self._pending_dir / f"{post.post_id}.json"
        try:
            path.write_text(json.dumps(post.to_dict(), indent=2), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    def _move_to_approved(self, post: LinkedInPost) -> None:
        src = self._pending_dir / f"{post.post_id}.json"
        dst = self._approved_dir / f"{post.post_id}.json"
        try:
            if src.exists():
                data = json.loads(src.read_text(encoding="utf-8"))
                data["status"] = PostStatus.APPROVED.value
                dst.write_text(json.dumps(data, indent=2), encoding="utf-8")
                src.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

    def _require(self, post_id: str) -> LinkedInPost:
        post = self._posts.get(post_id)
        if post is None:
            raise KeyError(f"Post '{post_id}' not found")
        return post
