"""
EMAIL_MCP_ACTION_SKILL — Phase 1
MCP-style action skill for sending emails with HITL enforcement.

Constitution compliance:
  - Section 9: Skill Design Rules (atomic, composable, testable)
  - Principle III: HITL by Default (Tier 3 → HITL required)
  - Section 8: Credential Storage (credentials_name is a reference only)
  - Principle VI: Fail Safe — denied on HITL failure

Public surface::

    from skills.actions.email import EmailActionSkill, EmailConfig, make_email_request

    config = EmailConfig(sender_address="agent@company.com", vault_root="/vault")
    skill  = EmailActionSkill(config)
    result = skill.send(to=["user@example.com"], subject="Hello", body="Hi!")
    print(result.status)   # PENDING_APPROVAL (tier 3 → HITL required by default)

    # With HITL skill (tier < 2 → direct send):
    skill_low = EmailActionSkill(EmailConfig("sender@x.com", default_tier=1))
    result2   = skill_low.send(to=["x@y.com"], subject="Low-risk", body="body")
    print(result2.status)  # SENT
"""

from __future__ import annotations

from typing import Any, Optional

from .action import EmailAction, ValidationError
from .adapter import EmailAdapter, MockEmailAdapter, RealEmailAdapter
from .logger import EmailActionLogger
from .models import (
    EmailActionStatus,
    EmailConfig,
    EmailEventType,
    EmailRequest,
    EmailResult,
    make_email_request,
)


class EmailActionSkill:
    """
    High-level facade for EMAIL_MCP_ACTION_SKILL Phase 1.

    Composes: EmailAction + EmailAdapter + EmailActionLogger.
    Optionally integrates with:
      - HITLSkill    (required for Tier ≥ 2 sends)
      - SecuritySkill (credential spec registration)
      - OrchestratorSkill SkillRegistry (MCP action registration)
    """

    def __init__(
        self,
        config: EmailConfig,
        adapter: Optional[EmailAdapter] = None,
        hitl_skill: Optional[Any] = None,
        security_skill: Optional[Any] = None,
        orchestrator_registry: Optional[Any] = None,
    ) -> None:
        self._config  = config
        self._adapter = adapter or MockEmailAdapter()
        self._logger  = EmailActionLogger(config.vault_root)
        self._action  = EmailAction(
            config=config,
            adapter=self._adapter,
            logger=self._logger,
            hitl_skill=hitl_skill,
        )

        if security_skill is not None:
            self._register_credential_spec(security_skill)

        if orchestrator_registry is not None:
            self._register_with_orchestrator(orchestrator_registry)

    # ------------------------------------------------------------------
    # Main interface
    # ------------------------------------------------------------------

    def send(
        self,
        to: list[str] | str,
        subject: str,
        body: str,
        cc: Optional[list[str]] = None,
        bcc: Optional[list[str]] = None,
        attachment_names: Optional[list[str]] = None,
        tier: Optional[int] = None,
    ) -> EmailResult:
        """
        Submit an email send request.

        Returns EmailResult with status:
          - SENT             : sent immediately (tier < 2 or no HITL skill)
          - PENDING_APPROVAL : queued for human review (tier ≥ 2 + HITL skill)
          - DENIED           : HITL submission failed (fail-safe)
          - FAILED           : validation or adapter error
        """
        request = make_email_request(
            to=to,
            subject=subject,
            body=body,
            sender=self._config.sender_address,
            cc=cc,
            bcc=bcc,
            attachment_names=attachment_names,
            tier=tier if tier is not None else self._config.default_tier,
            credentials_name=self._config.credentials_name,
        )
        return self._action.submit(request)

    def send_request(self, request: EmailRequest) -> EmailResult:
        """Submit a pre-built EmailRequest directly."""
        return self._action.submit(request)

    def health_check(self) -> bool:
        """Return True if the email adapter is healthy."""
        return self._action.health_check()

    # ------------------------------------------------------------------
    # HITL integration
    # ------------------------------------------------------------------

    def set_hitl(self, hitl_skill: Any) -> None:
        """Attach a HITLSkill for Tier ≥ 2 routing."""
        self._action._hitl = hitl_skill

    # ------------------------------------------------------------------
    # Logging / introspection
    # ------------------------------------------------------------------

    def read_logs(self, date: Optional[str] = None) -> list[dict]:
        """Return email log entries for a given date (YYYY-MM-DD). Default: today."""
        return self._logger.read_entries(date)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> EmailConfig:
        return self._config

    @property
    def adapter(self) -> EmailAdapter:
        return self._adapter

    @property
    def logger(self) -> EmailActionLogger:
        return self._logger

    @property
    def action(self) -> EmailAction:
        return self._action

    # ------------------------------------------------------------------
    # Security integration
    # ------------------------------------------------------------------

    def _register_credential_spec(self, security_skill: Any) -> None:
        """Register a CredentialSpec for the SMTP credential with SecuritySkill."""
        try:
            from bronze_tier_governance.security.models import (
                CredentialSpec,
                CredentialType,
            )
            spec = CredentialSpec(
                name=self._config.credentials_name,
                env_key=self._config.credentials_name.upper(),
                cred_type=CredentialType.API_KEY,
                description=f"SMTP/Email credential for {self._config.sender_address}",
                required=True,
            )
            security_skill.register(spec)
        except Exception:  # noqa: BLE001
            pass  # Non-fatal — security integration is optional in Phase 1

    # ------------------------------------------------------------------
    # Orchestrator integration (MCP action registration)
    # ------------------------------------------------------------------

    def _register_with_orchestrator(self, registry: Any) -> None:
        """Register email.send as an MCP action in the SkillRegistry."""
        try:
            def _send_handler(**kwargs: Any) -> dict:
                to      = kwargs.get("to", [])
                subject = kwargs.get("subject", "")
                body    = kwargs.get("body", "")
                tier    = kwargs.get("tier", self._config.default_tier)
                result  = self.send(to=to, subject=subject, body=body, tier=tier)
                return result.to_dict()

            registry.register("email", "send", _send_handler)
        except Exception:  # noqa: BLE001
            pass  # Non-fatal


__all__ = [
    # Facade
    "EmailActionSkill",
    # Config / models
    "EmailConfig",
    "EmailRequest",
    "EmailResult",
    "EmailActionStatus",
    "EmailEventType",
    "make_email_request",
    # Adapters
    "EmailAdapter",
    "MockEmailAdapter",
    "RealEmailAdapter",
    # Action
    "EmailAction",
    "ValidationError",
    # Logger
    "EmailActionLogger",
]
