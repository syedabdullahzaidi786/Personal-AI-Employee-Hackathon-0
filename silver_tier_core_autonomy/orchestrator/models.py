"""
ORCHESTRATOR_SYSTEM_SKILL — Data Models
Phase 1: Workflow, step, result, and run structures.

Constitution compliance:
  - Principle IV: Composability Through Standards (atomic skills, composable workflows)
  - Principle II: Explicit Over Implicit (declared intent per step)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Status enums
# ---------------------------------------------------------------------------

class StepStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    SUCCESS   = "success"
    FAILED    = "failed"
    SKIPPED   = "skipped"
    BLOCKED   = "blocked"    # HITL denied
    WAITING   = "waiting"    # Awaiting HITL decision


class WorkflowStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"  # All steps finished (some may be skipped/blocked)
    FAILED    = "failed"     # Stopped due to step failure with on_failure=stop
    ABORTED   = "aborted"    # External abort request


class OnFailure(str, Enum):
    STOP     = "stop"        # Halt entire workflow
    CONTINUE = "continue"    # Move to next step regardless
    SKIP     = "skip"        # Skip this step, mark skipped, continue


# ---------------------------------------------------------------------------
# Workflow Step
# ---------------------------------------------------------------------------

@dataclass
class WorkflowStep:
    """
    A single unit of work in a workflow.

    The orchestrator maps `skill_name + operation` to a registered skill handler.
    `params` are passed to the handler; template refs like ``{step_id.output.key}``
    are resolved at runtime from earlier steps' outputs.
    """
    id: str
    skill_name: str               # e.g. "filesystem", "hitl", "custom"
    operation: str                # handler name within the skill
    params: dict[str, Any] = field(default_factory=dict)
    tier: int = 1                 # HITL tier; >=2 requires human approval
    depends_on: list[str] = field(default_factory=list)  # step IDs
    on_failure: OnFailure = OnFailure.STOP
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "skill_name": self.skill_name,
            "operation": self.operation,
            "params": self.params,
            "tier": self.tier,
            "depends_on": self.depends_on,
            "on_failure": self.on_failure.value,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowStep":
        return cls(
            id=d["id"],
            skill_name=d["skill_name"],
            operation=d["operation"],
            params=d.get("params", {}),
            tier=d.get("tier", 1),
            depends_on=d.get("depends_on", []),
            on_failure=OnFailure(d.get("on_failure", "stop")),
            description=d.get("description", ""),
        )


# ---------------------------------------------------------------------------
# Step Result
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    step_id: str
    status: StepStatus
    output: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    hitl_request_id: Optional[str] = None   # Set when HITL gate triggered

    @property
    def duration_ms(self) -> float:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds() * 1000
        return 0.0

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": round(self.duration_ms, 2),
            "hitl_request_id": self.hitl_request_id,
        }


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

@dataclass
class Workflow:
    """
    A named, ordered sequence of WorkflowSteps.

    Workflows are the primary unit of work submitted to the OrchestratorSkill.
    """
    id: str
    name: str
    steps: list[WorkflowStep]
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def step_by_id(self, step_id: str) -> Optional[WorkflowStep]:
        return next((s for s in self.steps if s.id == step_id), None)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Workflow":
        return cls(
            id=d["id"],
            name=d["name"],
            description=d.get("description", ""),
            tags=d.get("tags", []),
            steps=[WorkflowStep.from_dict(s) for s in d.get("steps", [])],
        )


# ---------------------------------------------------------------------------
# Workflow Run  (runtime state of one execution)
# ---------------------------------------------------------------------------

@dataclass
class WorkflowRun:
    run_id: str
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    step_results: dict[str, StepResult] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    triggered_by: str = "manual"
    context: dict[str, Any] = field(default_factory=dict)   # Arbitrary caller context

    @property
    def duration_ms(self) -> float:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds() * 1000
        return 0.0

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "triggered_by": self.triggered_by,
            "context": self.context,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": round(self.duration_ms, 2),
            "step_results": {k: v.to_dict() for k, v in self.step_results.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowRun":
        run = cls(
            run_id=d["run_id"],
            workflow_id=d["workflow_id"],
            workflow_name=d["workflow_name"],
            status=WorkflowStatus(d.get("status", "pending")),
            triggered_by=d.get("triggered_by", "manual"),
            context=d.get("context", {}),
        )
        if d.get("started_at"):
            run.started_at = datetime.fromisoformat(d["started_at"])
        if d.get("finished_at"):
            run.finished_at = datetime.fromisoformat(d["finished_at"])
        for sid, srd in d.get("step_results", {}).items():
            sr = StepResult(
                step_id=srd["step_id"],
                status=StepStatus(srd["status"]),
                output=srd.get("output", {}),
                error=srd.get("error"),
                hitl_request_id=srd.get("hitl_request_id"),
            )
            if srd.get("started_at"):
                sr.started_at = datetime.fromisoformat(srd["started_at"])
            if srd.get("finished_at"):
                sr.finished_at = datetime.fromisoformat(srd["finished_at"])
            run.step_results[sid] = sr
        return run


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_run(workflow: Workflow, triggered_by: str = "manual", context: Optional[dict] = None) -> WorkflowRun:
    return WorkflowRun(
        run_id=f"RUN-{uuid.uuid4()}",
        workflow_id=workflow.id,
        workflow_name=workflow.name,
        triggered_by=triggered_by,
        context=context or {},
    )
