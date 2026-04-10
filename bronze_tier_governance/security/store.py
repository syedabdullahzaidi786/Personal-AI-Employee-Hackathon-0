"""
SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL — Credential Store
In-memory registry of named credentials with policy enforcement.

Constitution compliance:
  - Section 8: Secrets never stored in vault plaintext
  - Section 8: Never log credential values
  - "Least Privilege" — every access goes through the policy engine

Design invariants:
  - Credential VALUES are held only in the in-memory ``_values`` dict.
  - No value is ever written to disk, logged, or included in to_dict().
  - The store is populated at startup from env/dotenv via the loader.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .audit import SecurityAuditLogger
from .loader import CredentialLoader
from .models import CredentialSource, CredentialSpec, make_audit_entry
from .policy import AccessPolicy, PolicyViolation
from .redactor import SecretRedactor


class CredentialNotFoundError(Exception):
    """Raised when the requested credential has not been registered."""


class CredentialStore:
    """
    Central in-memory registry of credential specs and their runtime values.

    Values never leave memory (no disk write, no log, no dict serialisation).

    Usage::

        store = CredentialStore(policy, loader, redactor, audit)

        # Register a spec
        store.register(CredentialSpec("gmail_key", env_key="GMAIL_API_KEY"))

        # Load values from environment
        store.load_all()

        # Retrieve a value (policy checked)
        value = store.get("gmail_key", agent_id="gmail-watcher")
    """

    def __init__(
        self,
        policy:   AccessPolicy,
        loader:   CredentialLoader,
        redactor: SecretRedactor,
        audit:    SecurityAuditLogger,
    ) -> None:
        self._policy   = policy
        self._loader   = loader
        self._redactor = redactor
        self._audit    = audit
        # Spec registry (safe to inspect)
        self._specs:  dict[str, CredentialSpec] = {}
        # Value store — SECRET VALUES, never serialised or logged
        self._values: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, spec: CredentialSpec) -> None:
        """Register a credential spec. Does not load the value yet."""
        self._specs[spec.name] = spec

    def register_many(self, specs: list[CredentialSpec]) -> None:
        for spec in specs:
            self.register(spec)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, cred_name: str) -> bool:
        """
        Load the value for *cred_name* from the environment.

        Returns True if successfully loaded, False if the env var is unset
        and the credential is not required.
        Raises ``CredentialError`` if required but missing.
        """
        spec = self._specs.get(cred_name)
        if spec is None:
            raise CredentialNotFoundError(f"No spec registered for '{cred_name}'")

        if spec.required:
            value = self._loader.require(spec.env_key)
        else:
            value = self._loader.get(spec.env_key)  # type: ignore[assignment]
            if value is None:
                return False

        self._values[cred_name] = value
        self._redactor.register_secret(value)
        self._audit.log_load(cred_name, spec.env_key, source=CredentialSource.ENV_VAR)
        return True

    def load_all(self) -> dict[str, bool]:
        """
        Load all registered specs. Returns {cred_name: loaded_ok}.
        """
        results = {}
        for name in self._specs:
            try:
                results[name] = self.load(name)
            except Exception as exc:  # noqa: BLE001
                results[name] = False
                self._audit.log_error(name, str(exc))
        return results

    # ------------------------------------------------------------------
    # Retrieval (policy-enforced)
    # ------------------------------------------------------------------

    def get(self, cred_name: str, agent_id: str) -> str:
        """
        Return the credential value for *agent_id*.

        Raises:
          - ``CredentialNotFoundError`` if the spec is not registered or value not loaded.
          - ``PolicyViolation`` if the agent is not allowed.
        """
        if cred_name not in self._specs:
            raise CredentialNotFoundError(f"No spec registered for '{cred_name}'")

        # Policy check (always before value access)
        try:
            self._policy.check(agent_id, cred_name)
        except PolicyViolation:
            self._audit.log_denied(cred_name, agent_id)
            raise

        if cred_name not in self._values:
            raise CredentialNotFoundError(
                f"Credential '{cred_name}' registered but not loaded. Call load() first."
            )

        self._audit.log_access(cred_name, agent_id)
        return self._values[cred_name]

    def get_safe(self, cred_name: str, agent_id: str) -> Optional[str]:
        """Like ``get`` but returns None instead of raising."""
        try:
            return self.get(cred_name, agent_id)
        except (CredentialNotFoundError, PolicyViolation):
            return None

    # ------------------------------------------------------------------
    # Introspection (no values exposed)
    # ------------------------------------------------------------------

    def is_loaded(self, cred_name: str) -> bool:
        return cred_name in self._values

    def list_specs(self) -> list[CredentialSpec]:
        return list(self._specs.values())

    def list_loaded(self) -> list[str]:
        return list(self._values.keys())

    def rotation_due(self) -> list[CredentialSpec]:
        """Return specs whose rotation is overdue."""
        return [s for s in self._specs.values() if s.rotation_due]

    def to_safe_dict(self) -> dict:
        """
        Return a JSON-serialisable summary with NO secret values.
        Suitable for status pages and logging.
        """
        return {
            name: {
                "loaded":        name in self._values,
                "env_key":       spec.env_key,
                "cred_type":     spec.cred_type.value,
                "required":      spec.required,
                "rotation_due":  spec.rotation_due,
                "days_until_rotation": spec.days_until_rotation,
                "last_rotated":  spec.last_rotated.isoformat() if spec.last_rotated else None,
            }
            for name, spec in self._specs.items()
        }

    def mark_rotated(self, cred_name: str) -> None:
        """Record that a credential was manually rotated."""
        spec = self._specs.get(cred_name)
        if spec:
            spec.last_rotated = datetime.now(tz=timezone.utc)
            # Clear old value; caller must reload
            self._values.pop(cred_name, None)
            self._audit.log_rotation(cred_name)
