"""
Unit tests for Golden Tier — LinkedIn Watcher + Post Action.
Covers: models, client, watcher, poster, logger.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from golden_tier_external_world.watchers.linkedin.models import (
    LinkedInActivity,
    LinkedInConfig,
    LinkedInEventType,
)
from golden_tier_external_world.watchers.linkedin.client import (
    MockLinkedInClient,
    RealLinkedInClient,
)
from golden_tier_external_world.watchers.linkedin.watcher import LinkedInWatcher
from golden_tier_external_world.watchers.linkedin.logger import LinkedInWatcherLogger
from golden_tier_external_world.actions.linkedin.models import (
    LinkedInPost,
    PostResult,
    PostStatus,
    PostType,
)
from golden_tier_external_world.actions.linkedin.poster import LinkedInPoster
from golden_tier_external_world.actions.linkedin.logger import LinkedInPostLogger


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def mock_client() -> MockLinkedInClient:
    return MockLinkedInClient()


@pytest.fixture
def mock_client_with_data() -> MockLinkedInClient:
    activities = [
        MockLinkedInClient.make_activity(LinkedInEventType.NEW_MESSAGE, "ACT-001"),
        MockLinkedInClient.make_activity(LinkedInEventType.CONNECTION_REQUEST, "ACT-002"),
        MockLinkedInClient.make_activity(LinkedInEventType.POST_MENTION, "ACT-003"),
    ]
    return MockLinkedInClient(activities=activities)


@pytest.fixture
def linkedin_config(tmp_vault: Path) -> LinkedInConfig:
    return LinkedInConfig(vault_root=str(tmp_vault))


@pytest.fixture
def watcher(linkedin_config, mock_client_with_data) -> LinkedInWatcher:
    return LinkedInWatcher(linkedin_config, mock_client_with_data)


@pytest.fixture
def poster(tmp_vault: Path) -> LinkedInPoster:
    return LinkedInPoster(vault_root=tmp_vault)


# ---------------------------------------------------------------------------
# LinkedInActivity model tests
# ---------------------------------------------------------------------------

class TestLinkedInActivity:
    def test_to_dict_has_required_keys(self):
        activity = MockLinkedInClient.make_activity()
        d = activity.to_dict()
        assert "activity_id" in d
        assert "event_type" in d
        assert "sender_name" in d
        assert "content" in d

    def test_content_truncated_at_500(self):
        activity = LinkedInActivity(
            activity_id="A1",
            event_type=LinkedInEventType.NEW_MESSAGE,
            content="x" * 600,
        )
        d = activity.to_dict()
        assert len(d["content"]) <= 500


class TestLinkedInConfig:
    def test_default_poll_interval(self):
        config = LinkedInConfig()
        assert config.poll_interval_secs == 300.0

    def test_default_event_types_includes_messages(self):
        config = LinkedInConfig()
        assert LinkedInEventType.NEW_MESSAGE in config.event_types


# ---------------------------------------------------------------------------
# MockLinkedInClient tests
# ---------------------------------------------------------------------------

class TestMockLinkedInClient:
    def test_health_check_returns_true(self, mock_client):
        assert mock_client.health_check() is True

    def test_unhealthy_client(self):
        client = MockLinkedInClient(healthy=False)
        assert client.health_check() is False

    def test_fetch_returns_activities(self, mock_client_with_data):
        results = mock_client_with_data.fetch_activity()
        assert len(results) == 3

    def test_fetch_respects_max_results(self, mock_client_with_data):
        results = mock_client_with_data.fetch_activity(max_results=2)
        assert len(results) == 2

    def test_fetch_filters_by_event_type(self, mock_client_with_data):
        results = mock_client_with_data.fetch_activity(
            event_types=[LinkedInEventType.NEW_MESSAGE]
        )
        assert all(a.event_type == LinkedInEventType.NEW_MESSAGE for a in results)

    def test_fetch_raises_when_configured(self):
        client = MockLinkedInClient(raise_on_fetch=True)
        with pytest.raises(ConnectionError):
            client.fetch_activity()

    def test_make_activity_factory(self):
        activity = MockLinkedInClient.make_activity(LinkedInEventType.CONNECTION_REQUEST)
        assert activity.event_type == LinkedInEventType.CONNECTION_REQUEST
        assert activity.activity_id.startswith("LI-")

    def test_empty_client_returns_empty_list(self, mock_client):
        results = mock_client.fetch_activity()
        assert results == []


class TestRealLinkedInClient:
    def test_health_check_false_without_browser(self):
        client = RealLinkedInClient()
        assert client.health_check() is False

    def test_fetch_raises_without_browser(self):
        client = RealLinkedInClient()
        with pytest.raises((RuntimeError, NotImplementedError)):
            client.fetch_activity()


# ---------------------------------------------------------------------------
# LinkedInWatcher tests
# ---------------------------------------------------------------------------

class TestLinkedInWatcher:
    def test_start_and_health_check(self, watcher):
        watcher.start()
        assert watcher.health_check() is True

    def test_tick_returns_new_events(self, watcher):
        watcher.start()
        result = watcher.tick()
        assert result.events_found == 3

    def test_deduplication_no_repeat_events(self, watcher):
        watcher.start()
        result1 = watcher.tick()
        result2 = watcher.tick()
        assert result1.events_found == 3
        assert result2.events_found == 0  # already seen

    def test_seen_ids_persisted(self, linkedin_config, mock_client_with_data, tmp_vault):
        w1 = LinkedInWatcher(linkedin_config, mock_client_with_data)
        w1.start()
        w1.tick()

        # New watcher instance — should load seen IDs from disk
        activities = [
            MockLinkedInClient.make_activity(LinkedInEventType.NEW_MESSAGE, "ACT-001"),
        ]
        w2 = LinkedInWatcher(linkedin_config, MockLinkedInClient(activities=activities))
        w2.start()
        result = w2.tick()
        assert result.events_found == 0  # ACT-001 already seen

    def test_tick_never_raises_on_client_error(self, linkedin_config, tmp_vault):
        client = MockLinkedInClient(raise_on_fetch=True)
        watcher = LinkedInWatcher(linkedin_config, client)
        watcher.start()
        result = watcher.tick()  # Should not raise
        assert result is not None

    def test_health_check_false_when_unhealthy(self, linkedin_config, tmp_vault):
        client = MockLinkedInClient(healthy=False)
        watcher = LinkedInWatcher(linkedin_config, client)
        assert watcher.health_check() is False

    def test_event_payload_contains_activity_data(self, watcher):
        watcher.start()
        result = watcher.tick()
        assert result.events_found > 0  # we have 3 mock activities

    def test_watcher_type_is_linkedin(self, watcher):
        assert watcher._config.watcher_type == "linkedin"


# ---------------------------------------------------------------------------
# LinkedInWatcherLogger tests
# ---------------------------------------------------------------------------

class TestLinkedInWatcherLogger:
    def test_log_creates_file(self, tmp_vault):
        logger = LinkedInWatcherLogger(tmp_vault)
        logger.info("test")
        log_dir = tmp_vault / "70-LOGS" / "watchers" / "linkedin"
        assert len(list(log_dir.glob("*.jsonl"))) == 1

    def test_log_poll_entry(self, tmp_vault):
        logger = LinkedInWatcherLogger(tmp_vault)
        logger.log_poll(new_count=3, total_seen=10)
        log_file = list((tmp_vault / "70-LOGS" / "watchers" / "linkedin").glob("*.jsonl"))[0]
        content = log_file.read_text()
        assert "3" in content


# ---------------------------------------------------------------------------
# LinkedInPost model tests
# ---------------------------------------------------------------------------

class TestLinkedInPost:
    def test_default_status_draft(self):
        post = LinkedInPost(content="Hello!")
        assert post.status == PostStatus.DRAFT

    def test_post_id_prefix(self):
        post = LinkedInPost(content="Hello!")
        assert post.post_id.startswith("POST-")

    def test_to_full_text_with_hashtags(self):
        post = LinkedInPost(content="Launch!", hashtags=["AI", "startup"])
        full = post.to_full_text()
        assert "#AI" in full
        assert "#startup" in full

    def test_to_full_text_with_url(self):
        post = LinkedInPost(content="Check this out", url="https://example.com")
        full = post.to_full_text()
        assert "https://example.com" in full

    def test_to_full_text_no_extras(self):
        post = LinkedInPost(content="Simple post")
        full = post.to_full_text()
        assert "Simple post" in full

    def test_to_dict_has_required_keys(self):
        post = LinkedInPost(content="test")
        d = post.to_dict()
        assert "post_id" in d
        assert "content" in d
        assert "status" in d


# ---------------------------------------------------------------------------
# LinkedInPoster tests
# ---------------------------------------------------------------------------

class TestLinkedInPoster:
    def test_draft_creates_post(self, poster):
        post = poster.draft("Excited to share our new AI product! #AI")
        assert post.post_id.startswith("POST-")
        assert post.status == PostStatus.PENDING

    def test_draft_empty_content_raises(self, poster):
        with pytest.raises(ValueError):
            poster.draft("   ")

    def test_draft_writes_to_pending_dir(self, poster, tmp_vault):
        post = poster.draft("Test post")
        pending = list((tmp_vault / "Pending_Approval").glob("*.json"))
        assert len(pending) == 1

    def test_approve_changes_status(self, poster):
        post = poster.draft("Test post")
        approved = poster.approve(post.post_id)
        assert approved.status == PostStatus.APPROVED

    def test_approve_moves_to_approved_dir(self, poster, tmp_vault):
        post = poster.draft("Test post")
        poster.approve(post.post_id)
        approved_files = list((tmp_vault / "Approved").glob("*.json"))
        assert len(approved_files) == 1

    def test_publish_requires_approval(self, poster):
        post = poster.draft("Not approved post")
        result = poster.publish(post.post_id)
        assert result.status == PostStatus.FAILED
        assert "approval" in result.error.lower()

    def test_publish_approved_post_succeeds(self, poster):
        post = poster.draft("Business growth strategy #business")
        poster.approve(post.post_id)
        result = poster.publish(post.post_id)
        assert result.status == PostStatus.POSTED
        assert result.linkedin_post_id is not None

    def test_publish_unknown_post_fails(self, poster):
        result = poster.publish("NONEXISTENT-ID")
        assert result.status == PostStatus.FAILED
        assert "not found" in result.error

    def test_dry_run_does_not_publish(self, tmp_vault):
        poster = LinkedInPoster(vault_root=tmp_vault, dry_run=True)
        post = poster.draft("Dry run test")
        poster.approve(post.post_id)
        result = poster.publish(post.post_id)
        assert result.status == PostStatus.POSTED
        assert "DRY-RUN" in result.linkedin_post_id

    def test_list_pending(self, poster):
        poster.draft("Post 1")
        poster.draft("Post 2")
        pending = poster.list_pending()
        assert len(pending) == 2

    def test_list_approved(self, poster):
        post = poster.draft("Post 1")
        poster.approve(post.post_id)
        approved = poster.list_approved()
        assert len(approved) == 1

    def test_get_post_returns_post(self, poster):
        post = poster.draft("Get me")
        retrieved = poster.get_post(post.post_id)
        assert retrieved is post

    def test_get_post_returns_none_for_unknown(self, poster):
        assert poster.get_post("UNKNOWN") is None

    def test_hashtags_in_published_post(self, poster):
        post = poster.draft("AI is changing business", hashtags=["AI", "business"])
        poster.approve(post.post_id)
        full_text = post.to_full_text()
        assert "#AI" in full_text
        assert "#business" in full_text

    def test_rate_limit_blocks_excess_posts(self, tmp_vault):
        poster = LinkedInPoster(vault_root=tmp_vault)
        # Fill up rate limit (5 posts/hour)
        poster._post_times = [0.0] * 5  # simulate 5 recent posts (monotonic 0.0)
        # Now patch monotonic to return a small value so they're "within the hour"
        import time as _time
        original = _time.monotonic
        try:
            _time.monotonic = lambda: 100.0  # 100 seconds since epoch (within 3600s)
            poster._post_times = [50.0, 60.0, 70.0, 80.0, 90.0]  # all within last hour
            post = poster.draft("Rate limited post")
            poster.approve(post.post_id)
            result = poster.publish(post.post_id)
            assert result.status == PostStatus.FAILED
            assert "rate limit" in result.error.lower()
        finally:
            _time.monotonic = original


# ---------------------------------------------------------------------------
# LinkedInPostLogger tests
# ---------------------------------------------------------------------------

class TestLinkedInPostLogger:
    def test_log_creates_file(self, tmp_vault):
        logger = LinkedInPostLogger(tmp_vault)
        logger.info("test")
        log_dir = tmp_vault / "70-LOGS" / "actions" / "linkedin"
        assert len(list(log_dir.glob("*.jsonl"))) == 1

    def test_audit_log_created_on_publish(self, tmp_vault):
        logger = LinkedInPostLogger(tmp_vault)
        logger.log_post_published("POST-001", "LI-12345")
        audit_dir = tmp_vault / "70-LOGS" / "audit"
        audit_files = list(audit_dir.glob("*.jsonl"))
        assert len(audit_files) == 1
        content = audit_files[0].read_text()
        assert "POST-001" in content

    def test_error_level_on_failure(self, tmp_vault):
        logger = LinkedInPostLogger(tmp_vault)
        logger.log_post_failed("POST-001", "Browser MCP unavailable")
        log_file = list((tmp_vault / "70-LOGS" / "actions" / "linkedin").glob("*.jsonl"))[0]
        content = log_file.read_text()
        assert "ERROR" in content
