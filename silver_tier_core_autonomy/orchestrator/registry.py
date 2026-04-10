"""
ORCHESTRATOR_SYSTEM_SKILL — Skill Registry
Maps (skill_name, operation) pairs to callable Python handlers.
"""

from __future__ import annotations

from typing import Any, Callable, Optional


# A handler is any callable that accepts **kwargs and returns a dict
Handler = Callable[..., dict[str, Any]]


class RegistrationError(Exception):
    """Raised when a duplicate or invalid registration is attempted."""


class LookupError(Exception):  # noqa: A001
    """Raised when a requested skill/operation is not registered."""


class SkillRegistry:
    """
    Central registry that maps ``(skill_name, operation)`` to a Python callable.

    Usage::

        registry = SkillRegistry()
        registry.register("filesystem", "rename", my_rename_fn)

        handler = registry.get("filesystem", "rename")
        result  = handler(source="a.md", destination="b.md")
    """

    def __init__(self) -> None:
        # {skill_name: {operation: handler}}
        self._handlers: dict[str, dict[str, Handler]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        skill_name: str,
        operation: str,
        handler: Handler,
        *,
        overwrite: bool = False,
    ) -> None:
        """Register a handler for ``skill_name.operation``.

        Parameters
        ----------
        skill_name:
            Logical skill name (e.g. ``"filesystem"``, ``"hitl"``).
        operation:
            Operation/method name within the skill (e.g. ``"rename"``).
        handler:
            Callable that accepts keyword arguments and returns a ``dict``.
        overwrite:
            If ``False`` (default) raise ``RegistrationError`` on duplicate.
        """
        if not skill_name or not operation:
            raise RegistrationError("skill_name and operation must be non-empty strings")
        if not callable(handler):
            raise RegistrationError(f"handler for {skill_name}.{operation} must be callable")

        ops = self._handlers.setdefault(skill_name, {})
        if operation in ops and not overwrite:
            raise RegistrationError(
                f"Handler already registered for {skill_name}.{operation}. "
                "Use overwrite=True to replace."
            )
        ops[operation] = handler

    def register_skill(
        self,
        skill_name: str,
        operations: dict[str, Handler],
        *,
        overwrite: bool = False,
    ) -> None:
        """Batch-register multiple operations for a single skill."""
        for operation, handler in operations.items():
            self.register(skill_name, operation, handler, overwrite=overwrite)

    def unregister(self, skill_name: str, operation: Optional[str] = None) -> None:
        """Remove a handler or an entire skill from the registry."""
        if operation is None:
            self._handlers.pop(skill_name, None)
        else:
            ops = self._handlers.get(skill_name, {})
            ops.pop(operation, None)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, skill_name: str, operation: str) -> Handler:
        """Return the handler for ``skill_name.operation``.

        Raises ``LookupError`` if not found.
        """
        ops = self._handlers.get(skill_name)
        if ops is None:
            raise LookupError(f"No skill registered with name '{skill_name}'")
        handler = ops.get(operation)
        if handler is None:
            raise LookupError(
                f"No operation '{operation}' registered for skill '{skill_name}'. "
                f"Available: {sorted(ops.keys())}"
            )
        return handler

    def has(self, skill_name: str, operation: str) -> bool:
        """Return ``True`` if the (skill_name, operation) pair is registered."""
        return operation in self._handlers.get(skill_name, {})

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_skills(self) -> list[str]:
        """Return sorted list of registered skill names."""
        return sorted(self._handlers.keys())

    def list_operations(self, skill_name: str) -> list[str]:
        """Return sorted list of operations for a skill (empty list if unknown)."""
        return sorted(self._handlers.get(skill_name, {}).keys())

    def to_dict(self) -> dict[str, list[str]]:
        """Return a JSON-serialisable mapping of skill → [operations]."""
        return {s: self.list_operations(s) for s in self.list_skills()}
