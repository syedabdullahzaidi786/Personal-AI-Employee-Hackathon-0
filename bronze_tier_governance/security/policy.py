"""
SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL — Access Policy
Least-privilege enforcement: default-deny, explicit allow required.

Constitution compliance:
  - Section 8: "Least Privilege — agents get minimum necessary permissions"
  - "Zero Trust — verify every action, even from trusted agents"
"""

from __future__ import annotations

from typing import Optional

from .models import PolicyEffect, PolicyRule


class PolicyViolation(Exception):
    """Raised when an access attempt is denied by policy."""


class AccessPolicy:
    """
    Manages a list of PolicyRule objects.

    Resolution order (first matching rule wins):
      1. Explicit DENY rules are checked first.
      2. Explicit ALLOW rules are checked second.
      3. Default is DENY if no rule matches.

    Usage::

        policy = AccessPolicy()
        policy.add_rule(PolicyRule("gmail-watcher", "gmail_api_key", PolicyEffect.ALLOW))
        policy.add_rule(PolicyRule("*", "*", PolicyEffect.DENY))  # deny everything else

        policy.check("gmail-watcher", "gmail_api_key")  # OK
        policy.check("other-agent", "gmail_api_key")    # raises PolicyViolation
    """

    def __init__(self, default_effect: PolicyEffect = PolicyEffect.DENY) -> None:
        self._rules: list[PolicyRule] = []
        self._default_effect = default_effect

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)

    def add_allow(self, agent_id: str, cred_name: str, reason: str = "") -> None:
        self._rules.append(PolicyRule(agent_id, cred_name, PolicyEffect.ALLOW, reason))

    def add_deny(self, agent_id: str, cred_name: str, reason: str = "") -> None:
        self._rules.append(PolicyRule(agent_id, cred_name, PolicyEffect.DENY, reason))

    def remove_rules_for(self, agent_id: str, cred_name: Optional[str] = None) -> None:
        self._rules = [
            r for r in self._rules
            if not (r.agent_id == agent_id and (cred_name is None or r.cred_name == cred_name))
        ]

    # ------------------------------------------------------------------
    # Enforcement
    # ------------------------------------------------------------------

    def check(self, agent_id: str, cred_name: str) -> None:
        """
        Verify *agent_id* may access *cred_name*.

        Raises ``PolicyViolation`` if denied.
        """
        effect = self.evaluate(agent_id, cred_name)
        if effect == PolicyEffect.DENY:
            raise PolicyViolation(
                f"Agent '{agent_id}' is not permitted to access credential '{cred_name}'. "
                f"Add an explicit ALLOW rule."
            )

    def is_allowed(self, agent_id: str, cred_name: str) -> bool:
        """Return True if the access is allowed, False otherwise."""
        return self.evaluate(agent_id, cred_name) == PolicyEffect.ALLOW

    def evaluate(self, agent_id: str, cred_name: str) -> PolicyEffect:
        """
        Evaluate rules and return the effective PolicyEffect.

        Deny rules checked first (explicit deny overrides allow).
        """
        # 1. Check for explicit DENY
        for rule in self._rules:
            if rule.effect == PolicyEffect.DENY and rule.matches(agent_id, cred_name):
                return PolicyEffect.DENY

        # 2. Check for explicit ALLOW
        for rule in self._rules:
            if rule.effect == PolicyEffect.ALLOW and rule.matches(agent_id, cred_name):
                return PolicyEffect.ALLOW

        # 3. Default
        return self._default_effect

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_rules(self) -> list[PolicyRule]:
        return list(self._rules)

    def allowed_credentials(self, agent_id: str, all_cred_names: list[str]) -> list[str]:
        """Return the subset of *all_cred_names* accessible to *agent_id*."""
        return [c for c in all_cred_names if self.is_allowed(agent_id, c)]

    def to_dict(self) -> dict:
        return {
            "default_effect": self._default_effect.value,
            "rules": [r.to_dict() for r in self._rules],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AccessPolicy":
        policy = cls(default_effect=PolicyEffect(d.get("default_effect", "deny")))
        for rd in d.get("rules", []):
            policy.add_rule(PolicyRule.from_dict(rd))
        return policy
