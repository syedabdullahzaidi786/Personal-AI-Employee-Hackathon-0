"""
RALPH_WIGGUM_LOOP_SKILL — Health Checker
Pings registered components and produces a HealthReport.

Constitution compliance:
  - Principle VI: Fail Safe  (health check failures are logged, not fatal)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .models import ComponentHealth, HealthReport, HealthState


# A health probe is a zero-argument callable returning True (healthy) or
# raising / returning False (unhealthy).
HealthProbe = Callable[[], bool]


class HealthChecker:
    """
    Manages health probes for all loop components.

    Usage::

        checker = HealthChecker()
        checker.register("filesystem", lambda: filesystem_skill.ping())
        checker.register("hitl_store", lambda: hitl_store_path.exists())

        report = checker.check_all()
        print(report.overall)   # HealthState.HEALTHY
    """

    def __init__(self) -> None:
        # {name: probe}
        self._probes: dict[str, HealthProbe] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, probe: HealthProbe) -> None:
        """Register a health probe for *name*."""
        if not callable(probe):
            raise ValueError(f"Probe for '{name}' must be callable")
        self._probes[name] = probe

    def unregister(self, name: str) -> None:
        self._probes.pop(name, None)

    def list_components(self) -> list[str]:
        return sorted(self._probes.keys())

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check(self, name: str) -> ComponentHealth:
        """Run the probe for a single component and return its health."""
        probe = self._probes.get(name)
        if probe is None:
            return ComponentHealth(
                name=name,
                state=HealthState.UNKNOWN,
                message="No probe registered",
                last_check=datetime.now(tz=timezone.utc),
            )
        return self._run_probe(name, probe)

    def check_all(self) -> HealthReport:
        """Run all probes and return an aggregated HealthReport."""
        now = datetime.now(tz=timezone.utc)
        results: list[ComponentHealth] = []

        for name, probe in sorted(self._probes.items()):
            results.append(self._run_probe(name, probe))

        # Derive overall state
        if not results:
            overall = HealthState.HEALTHY   # nothing to check = healthy
        elif any(c.state == HealthState.UNHEALTHY for c in results):
            overall = HealthState.UNHEALTHY
        elif any(c.state == HealthState.DEGRADED for c in results):
            overall = HealthState.DEGRADED
        else:
            overall = HealthState.HEALTHY

        return HealthReport(checked_at=now, components=results, overall=overall)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_probe(self, name: str, probe: HealthProbe) -> ComponentHealth:
        t0 = time.perf_counter()
        now = datetime.now(tz=timezone.utc)
        try:
            result = probe()
            latency = (time.perf_counter() - t0) * 1000
            state   = HealthState.HEALTHY if result else HealthState.DEGRADED
            message = "ok" if result else "probe returned False"
        except Exception as exc:  # noqa: BLE001
            latency = (time.perf_counter() - t0) * 1000
            state   = HealthState.UNHEALTHY
            message = f"{type(exc).__name__}: {exc}"

        return ComponentHealth(
            name=name,
            state=state,
            last_check=now,
            message=message,
            latency_ms=round(latency, 2),
        )
