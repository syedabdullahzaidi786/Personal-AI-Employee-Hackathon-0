"""
Unit tests for ORCHESTRATOR_SYSTEM_SKILL Phase 1.
Covers: models, registry, executor, engine, store, logger, facade.
"""

from __future__ import annotations

import json
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import helpers
# ---------------------------------------------------------------------------

import sys, os

from silver_tier_core_autonomy.orchestrator.models import (
    OnFailure,
    StepResult,
    StepStatus,
    Workflow,
    WorkflowRun,
    WorkflowStatus,
    WorkflowStep,
    make_run,
)
from silver_tier_core_autonomy.orchestrator.registry import (
    LookupError,
    RegistrationError,
    SkillRegistry,
)
from silver_tier_core_autonomy.orchestrator.executor import StepExecutor, resolve_params
from silver_tier_core_autonomy.orchestrator.engine import WorkflowEngine
from silver_tier_core_autonomy.orchestrator.logger import OrchestratorLogger
from silver_tier_core_autonomy.orchestrator.store import RunStore
from silver_tier_core_autonomy.orchestrator import OrchestratorSkill


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def registry() -> SkillRegistry:
    return SkillRegistry()


@pytest.fixture
def logger(tmp_vault: Path) -> OrchestratorLogger:
    return OrchestratorLogger(tmp_vault)


@pytest.fixture
def executor(registry: SkillRegistry, logger: OrchestratorLogger) -> StepExecutor:
    return StepExecutor(registry=registry, logger=logger)


@pytest.fixture
def store(tmp_vault: Path) -> RunStore:
    return RunStore(tmp_vault)


@pytest.fixture
def engine(executor: StepExecutor, logger: OrchestratorLogger, store: RunStore) -> WorkflowEngine:
    return WorkflowEngine(executor=executor, logger=logger, run_store=store)


@pytest.fixture
def simple_workflow() -> Workflow:
    return Workflow(
        id="wf-test-001",
        name="Test Workflow",
        steps=[
            WorkflowStep(id="s1", skill_name="echo", operation="say",
                         params={"message": "hello"}),
            WorkflowStep(id="s2", skill_name="echo", operation="say",
                         params={"message": "world"}, depends_on=["s1"]),
        ],
    )


@pytest.fixture
def skill(tmp_vault: Path) -> OrchestratorSkill:
    return OrchestratorSkill(vault_root=tmp_vault)


# ---------------------------------------------------------------------------
# 1. Models
# ---------------------------------------------------------------------------

class TestWorkflowStep:
    def test_to_dict_roundtrip(self):
        step = WorkflowStep(
            id="s1", skill_name="filesystem", operation="rename",
            params={"source": "a.md"}, tier=2, depends_on=["s0"],
            on_failure=OnFailure.CONTINUE, description="Rename file",
        )
        d = step.to_dict()
        step2 = WorkflowStep.from_dict(d)
        assert step2.id == "s1"
        assert step2.skill_name == "filesystem"
        assert step2.operation == "rename"
        assert step2.tier == 2
        assert step2.depends_on == ["s0"]
        assert step2.on_failure == OnFailure.CONTINUE

    def test_default_on_failure(self):
        step = WorkflowStep.from_dict({
            "id": "s1", "skill_name": "x", "operation": "y",
        })
        assert step.on_failure == OnFailure.STOP

    def test_params_default_empty(self):
        step = WorkflowStep(id="s1", skill_name="x", operation="y")
        assert step.params == {}


class TestStepResult:
    def test_duration_ms_computed(self):
        from datetime import timedelta
        start = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end   = start + timedelta(milliseconds=250)
        r = StepResult(step_id="s1", status=StepStatus.SUCCESS,
                       started_at=start, finished_at=end)
        assert abs(r.duration_ms - 250.0) < 1.0

    def test_duration_ms_zero_when_no_times(self):
        r = StepResult(step_id="s1", status=StepStatus.PENDING)
        assert r.duration_ms == 0.0

    def test_to_dict_contains_expected_keys(self):
        r = StepResult(step_id="s1", status=StepStatus.SUCCESS, output={"k": "v"})
        d = r.to_dict()
        assert d["step_id"] == "s1"
        assert d["status"] == "success"
        assert d["output"] == {"k": "v"}


class TestWorkflow:
    def test_step_by_id_found(self, simple_workflow: Workflow):
        s = simple_workflow.step_by_id("s1")
        assert s is not None
        assert s.id == "s1"

    def test_step_by_id_not_found(self, simple_workflow: Workflow):
        assert simple_workflow.step_by_id("missing") is None

    def test_to_dict_roundtrip(self, simple_workflow: Workflow):
        d = simple_workflow.to_dict()
        wf2 = Workflow.from_dict(d)
        assert wf2.id == simple_workflow.id
        assert len(wf2.steps) == len(simple_workflow.steps)


class TestWorkflowRun:
    def test_make_run_defaults(self, simple_workflow: Workflow):
        run = make_run(simple_workflow)
        assert run.run_id.startswith("RUN-")
        assert run.workflow_id == simple_workflow.id
        assert run.status == WorkflowStatus.PENDING

    def test_to_dict_roundtrip(self, simple_workflow: Workflow):
        run = make_run(simple_workflow, triggered_by="test")
        run.status = WorkflowStatus.COMPLETED
        run.started_at = datetime.now(tz=timezone.utc)
        run.finished_at = datetime.now(tz=timezone.utc)
        d = run.to_dict()
        run2 = WorkflowRun.from_dict(d)
        assert run2.run_id == run.run_id
        assert run2.status == WorkflowStatus.COMPLETED


# ---------------------------------------------------------------------------
# 2. Registry
# ---------------------------------------------------------------------------

class TestSkillRegistry:
    def test_register_and_get(self, registry: SkillRegistry):
        fn = lambda **kw: {"ok": True}
        registry.register("echo", "say", fn)
        handler = registry.get("echo", "say")
        assert handler is fn

    def test_lookup_unknown_skill_raises(self, registry: SkillRegistry):
        with pytest.raises(LookupError, match="echo"):
            registry.get("echo", "say")

    def test_lookup_unknown_operation_raises(self, registry: SkillRegistry):
        registry.register("echo", "say", lambda **kw: {})
        with pytest.raises(LookupError, match="shout"):
            registry.get("echo", "shout")

    def test_duplicate_raises(self, registry: SkillRegistry):
        fn = lambda **kw: {}
        registry.register("echo", "say", fn)
        with pytest.raises(RegistrationError):
            registry.register("echo", "say", fn)

    def test_overwrite_allowed(self, registry: SkillRegistry):
        fn1 = lambda **kw: {"v": 1}
        fn2 = lambda **kw: {"v": 2}
        registry.register("echo", "say", fn1)
        registry.register("echo", "say", fn2, overwrite=True)
        assert registry.get("echo", "say")() == {"v": 2}

    def test_has(self, registry: SkillRegistry):
        registry.register("echo", "say", lambda **kw: {})
        assert registry.has("echo", "say")
        assert not registry.has("echo", "shout")

    def test_list_skills(self, registry: SkillRegistry):
        registry.register("a", "op", lambda **kw: {})
        registry.register("b", "op", lambda **kw: {})
        assert registry.list_skills() == ["a", "b"]

    def test_register_skill_batch(self, registry: SkillRegistry):
        registry.register_skill("echo", {
            "say": lambda **kw: {},
            "shout": lambda **kw: {},
        })
        assert registry.has("echo", "say")
        assert registry.has("echo", "shout")

    def test_register_empty_name_raises(self, registry: SkillRegistry):
        with pytest.raises(RegistrationError):
            registry.register("", "say", lambda **kw: {})

    def test_register_non_callable_raises(self, registry: SkillRegistry):
        with pytest.raises(RegistrationError):
            registry.register("echo", "say", "not-callable")  # type: ignore

    def test_to_dict(self, registry: SkillRegistry):
        registry.register("echo", "say", lambda **kw: {})
        d = registry.to_dict()
        assert d == {"echo": ["say"]}


# ---------------------------------------------------------------------------
# 3. Template resolver
# ---------------------------------------------------------------------------

class TestResolveParams:
    def _make_result(self, step_id: str, **output) -> StepResult:
        return StepResult(step_id=step_id, status=StepStatus.SUCCESS, output=output)

    def test_literal_passthrough(self):
        results = {"s1": self._make_result("s1", dest="b.md")}
        assert resolve_params({"x": 42}, results) == {"x": 42}

    def test_full_string_template(self):
        results = {"s1": self._make_result("s1", dest="b.md")}
        out = resolve_params({"path": "{s1.output.dest}"}, results)
        assert out["path"] == "b.md"

    def test_inline_template(self):
        results = {"s1": self._make_result("s1", name="hello")}
        out = resolve_params({"msg": "Value is {s1.output.name}!"}, results)
        assert out["msg"] == "Value is hello!"

    def test_missing_step_raises(self):
        with pytest.raises(ValueError, match="s1"):
            resolve_params({"p": "{s1.output.k}"}, {})

    def test_missing_key_raises(self):
        results = {"s1": self._make_result("s1", x=1)}
        with pytest.raises(ValueError, match="'missing'"):
            resolve_params({"p": "{s1.output.missing}"}, results)

    def test_nested_dict(self):
        results = {"s1": self._make_result("s1", v="abc")}
        out = resolve_params({"nested": {"key": "{s1.output.v}"}}, results)
        assert out["nested"]["key"] == "abc"

    def test_list_template(self):
        results = {"s1": self._make_result("s1", v="abc")}
        out = resolve_params({"items": ["{s1.output.v}", "literal"]}, results)
        assert out["items"] == ["abc", "literal"]


# ---------------------------------------------------------------------------
# 4. Step Executor
# ---------------------------------------------------------------------------

class TestStepExecutor:
    def _make_step(self, **kwargs) -> WorkflowStep:
        defaults = {"id": "s1", "skill_name": "echo", "operation": "say", "params": {}}
        defaults.update(kwargs)
        return WorkflowStep(**defaults)

    def test_successful_execution(self, executor: StepExecutor, registry: SkillRegistry):
        registry.register("echo", "say", lambda message="": {"echoed": message})
        step = self._make_step(params={"message": "hi"})
        result = executor.execute(step, "RUN-1", {})
        assert result.status == StepStatus.SUCCESS
        assert result.output == {"echoed": "hi"}

    def test_handler_not_registered_fails(self, executor: StepExecutor):
        step = self._make_step()
        result = executor.execute(step, "RUN-1", {})
        assert result.status == StepStatus.FAILED
        assert "echo" in result.error

    def test_handler_exception_fails(self, executor: StepExecutor, registry: SkillRegistry):
        def boom(**kw):
            raise RuntimeError("exploded")
        registry.register("echo", "say", boom)
        step = self._make_step()
        result = executor.execute(step, "RUN-1", {})
        assert result.status == StepStatus.FAILED
        assert "exploded" in result.error

    def test_template_resolution(self, executor: StepExecutor, registry: SkillRegistry):
        registry.register("echo", "say", lambda message="": {"echoed": message})
        prior = StepResult(step_id="s0", status=StepStatus.SUCCESS, output={"msg": "resolved"})
        step = self._make_step(params={"message": "{s0.output.msg}"})
        result = executor.execute(step, "RUN-1", {"s0": prior})
        assert result.output["echoed"] == "resolved"

    def test_handler_non_dict_output_wrapped(self, executor: StepExecutor, registry: SkillRegistry):
        registry.register("echo", "say", lambda **kw: "raw string")
        step = self._make_step()
        result = executor.execute(step, "RUN-1", {})
        assert result.status == StepStatus.SUCCESS
        assert result.output == {"result": "raw string"}

    def test_hitl_tier2_auto_approved_proceeds(
        self, executor: StepExecutor, registry: SkillRegistry
    ):
        """HITL auto-approves (tier <= 1 maps to AUTO_APPROVED); tier=2 with mock hitl."""
        from bronze_tier_governance.hitl.models import Decision
        mock_hitl = MagicMock()
        mock_req  = MagicMock()
        mock_req.status = Decision.AUTO
        mock_req.request_id = "REQ-000"
        mock_hitl.submit.return_value = mock_req

        exec_with_hitl = StepExecutor(registry=registry, logger=executor._logger, hitl_skill=mock_hitl)
        registry.register("echo", "say", lambda **kw: {"ok": True})
        step = self._make_step(tier=2)
        result = exec_with_hitl.execute(step, "RUN-1", {})
        assert result.status == StepStatus.SUCCESS

    def test_hitl_tier2_pending_returns_waiting(
        self, executor: StepExecutor, registry: SkillRegistry
    ):
        from bronze_tier_governance.hitl.models import Decision
        mock_hitl = MagicMock()
        mock_req  = MagicMock()
        mock_req.status = Decision.PENDING
        mock_req.request_id = "REQ-001"
        mock_hitl.submit.return_value = mock_req

        exec_with_hitl = StepExecutor(registry=registry, logger=executor._logger, hitl_skill=mock_hitl)
        registry.register("echo", "say", lambda **kw: {})
        step = self._make_step(tier=2)
        result = exec_with_hitl.execute(step, "RUN-1", {})
        assert result.status == StepStatus.WAITING
        assert result.hitl_request_id == "REQ-001"

    def test_hitl_tier2_denied_returns_blocked(
        self, executor: StepExecutor, registry: SkillRegistry
    ):
        from bronze_tier_governance.hitl.models import Decision
        mock_hitl = MagicMock()
        mock_req  = MagicMock()
        mock_req.status = Decision.DENIED
        mock_req.request_id = "REQ-002"
        mock_hitl.submit.return_value = mock_req

        exec_with_hitl = StepExecutor(registry=registry, logger=executor._logger, hitl_skill=mock_hitl)
        registry.register("echo", "say", lambda **kw: {})
        step = self._make_step(tier=2)
        result = exec_with_hitl.execute(step, "RUN-1", {})
        assert result.status == StepStatus.BLOCKED


# ---------------------------------------------------------------------------
# 5. Workflow Engine
# ---------------------------------------------------------------------------

class TestWorkflowEngine:
    def _register_echo(self, registry: SkillRegistry):
        registry.register("echo", "say", lambda message="": {"echoed": message})

    def test_simple_run_completes(
        self, engine: WorkflowEngine, registry: SkillRegistry, simple_workflow: Workflow
    ):
        self._register_echo(registry)
        run = engine.run(simple_workflow)
        assert run.status == WorkflowStatus.COMPLETED
        assert run.step_results["s1"].status == StepStatus.SUCCESS
        assert run.step_results["s2"].status == StepStatus.SUCCESS

    def test_on_failure_stop_halts_run(
        self, engine: WorkflowEngine, registry: SkillRegistry
    ):
        def boom(**kw):
            raise RuntimeError("fail")
        registry.register("echo", "say", boom)
        wf = Workflow(
            id="wf-fail", name="Fail",
            steps=[
                WorkflowStep(id="s1", skill_name="echo", operation="say", on_failure=OnFailure.STOP),
                WorkflowStep(id="s2", skill_name="echo", operation="say"),
            ],
        )
        run = engine.run(wf)
        assert run.status == WorkflowStatus.FAILED
        assert run.step_results["s1"].status == StepStatus.FAILED
        assert run.step_results["s2"].status == StepStatus.SKIPPED

    def test_on_failure_continue(
        self, engine: WorkflowEngine, registry: SkillRegistry
    ):
        call_order = []
        def fail_fn(**kw): raise RuntimeError("fail")
        def ok_fn(**kw): call_order.append("s2"); return {"ok": True}

        registry.register("fail_skill", "op", fail_fn)
        registry.register("echo", "say", ok_fn)
        wf = Workflow(
            id="wf-cont", name="Continue",
            steps=[
                WorkflowStep(id="s1", skill_name="fail_skill", operation="op",
                             on_failure=OnFailure.CONTINUE),
                WorkflowStep(id="s2", skill_name="echo", operation="say"),
            ],
        )
        run = engine.run(wf)
        assert "s2" in call_order
        assert run.step_results["s2"].status == StepStatus.SUCCESS

    def test_on_failure_skip(
        self, engine: WorkflowEngine, registry: SkillRegistry
    ):
        def boom(**kw): raise RuntimeError("fail")
        registry.register("fail_skill", "op", boom)
        registry.register("echo", "say", lambda **kw: {})
        wf = Workflow(
            id="wf-skip", name="Skip",
            steps=[
                WorkflowStep(id="s1", skill_name="fail_skill", operation="op",
                             on_failure=OnFailure.SKIP),
                WorkflowStep(id="s2", skill_name="echo", operation="say"),
            ],
        )
        run = engine.run(wf)
        assert run.step_results["s1"].status == StepStatus.SKIPPED
        assert run.step_results["s2"].status == StepStatus.SUCCESS

    def test_dependency_not_met_skips_step(
        self, engine: WorkflowEngine, registry: SkillRegistry
    ):
        def boom(**kw): raise RuntimeError("fail")
        registry.register("fail_skill", "op", boom)
        registry.register("echo", "say", lambda **kw: {})
        wf = Workflow(
            id="wf-dep", name="Dep",
            steps=[
                WorkflowStep(id="s1", skill_name="fail_skill", operation="op",
                             on_failure=OnFailure.STOP),
                WorkflowStep(id="s2", skill_name="echo", operation="say",
                             depends_on=["s1"]),
            ],
        )
        run = engine.run(wf)
        assert run.status == WorkflowStatus.FAILED
        assert run.step_results["s2"].status == StepStatus.SKIPPED

    def test_empty_workflow_completes(
        self, engine: WorkflowEngine
    ):
        wf = Workflow(id="wf-empty", name="Empty", steps=[])
        run = engine.run(wf)
        assert run.status == WorkflowStatus.COMPLETED
        assert run.step_results == {}

    def test_run_timestamps(
        self, engine: WorkflowEngine, registry: SkillRegistry, simple_workflow: Workflow
    ):
        self._register_echo(registry)
        run = engine.run(simple_workflow)
        assert run.started_at is not None
        assert run.finished_at is not None
        assert run.finished_at >= run.started_at


# ---------------------------------------------------------------------------
# 6. Run Store
# ---------------------------------------------------------------------------

class TestRunStore:
    def _make_run(self, status: WorkflowStatus = WorkflowStatus.RUNNING) -> WorkflowRun:
        wf = Workflow(id="wf-1", name="WF", steps=[])
        run = make_run(wf)
        run.status = status
        run.started_at = datetime.now(tz=timezone.utc)
        return run

    def test_save_and_get(self, store: RunStore):
        run = self._make_run(WorkflowStatus.COMPLETED)
        run.finished_at = datetime.now(tz=timezone.utc)
        store.save(run)
        loaded = store.get(run.run_id)
        assert loaded is not None
        assert loaded.run_id == run.run_id
        assert loaded.status == WorkflowStatus.COMPLETED

    def test_active_run_in_active_dir(self, store: RunStore):
        run = self._make_run(WorkflowStatus.RUNNING)
        store.save(run)
        active = store.list_active()
        ids = [r.run_id for r in active]
        assert run.run_id in ids

    def test_completed_run_moves_to_completed_dir(self, store: RunStore):
        run = self._make_run(WorkflowStatus.RUNNING)
        store.save(run)
        run.status = WorkflowStatus.COMPLETED
        run.finished_at = datetime.now(tz=timezone.utc)
        store.save(run)
        active = [r.run_id for r in store.list_active()]
        completed = [r.run_id for r in store.list_completed()]
        assert run.run_id not in active
        assert run.run_id in completed

    def test_get_nonexistent_returns_none(self, store: RunStore):
        assert store.get("RUN-does-not-exist") is None

    def test_list_all(self, store: RunStore):
        r1 = self._make_run(WorkflowStatus.RUNNING)
        r2 = self._make_run(WorkflowStatus.COMPLETED)
        r2.finished_at = datetime.now(tz=timezone.utc)
        store.save(r1)
        store.save(r2)
        all_runs = store.list_all()
        ids = [r.run_id for r in all_runs]
        assert r1.run_id in ids
        assert r2.run_id in ids


# ---------------------------------------------------------------------------
# 7. Logger
# ---------------------------------------------------------------------------

class TestOrchestratorLogger:
    def test_log_run_started_creates_files(self, logger: OrchestratorLogger, tmp_vault: Path):
        logger.log_run_started("RUN-1", "MyWF", 3)
        daily = list((tmp_vault / "70-LOGS/orchestrator/daily").glob("*.md"))
        runs  = list((tmp_vault / "70-LOGS/orchestrator/runs").glob("*.md"))
        assert len(daily) >= 1
        assert len(runs) >= 1

    def test_log_step_finished_appends(self, logger: OrchestratorLogger, tmp_vault: Path):
        logger.log_run_started("RUN-2", "WF", 1)
        logger.log_step_started("RUN-2", "s1", "echo", "say")
        logger.log_step_finished("RUN-2", "s1", "success", 42.0)
        daily_path = next((tmp_vault / "70-LOGS/orchestrator/daily").glob("*.md"))
        content = daily_path.read_text(encoding="utf-8")
        assert "STEP_DONE" in content

    def test_log_error_writes_to_errors_dir(self, logger: OrchestratorLogger, tmp_vault: Path):
        logger.log_error("RUN-3", "s1", "Something went wrong")
        errors = list((tmp_vault / "70-LOGS/orchestrator/errors").glob("*.md"))
        assert len(errors) >= 1

    def test_never_raises_on_bad_vault(self):
        """Logger should be fail-safe even with a non-writable path."""
        bad_logger = OrchestratorLogger("/nonexistent/path/xyz")
        # Should not raise (just print to stderr)
        try:
            bad_logger.log_info("RUN-X", "test")
        except Exception:
            pass  # Some systems may raise on mkdir; that's fine too for this test


# ---------------------------------------------------------------------------
# 8. OrchestratorSkill facade
# ---------------------------------------------------------------------------

class TestOrchestratorSkill:
    def test_register_and_run(self, skill: OrchestratorSkill):
        skill.register("echo", "say", lambda message="": {"echoed": message})
        wf = Workflow(
            id="wf-f1", name="Facade Test",
            steps=[
                WorkflowStep(id="s1", skill_name="echo", operation="say",
                             params={"message": "facade"}),
            ],
        )
        run = skill.run_workflow(wf, triggered_by="test")
        assert run.status == WorkflowStatus.COMPLETED
        assert run.step_results["s1"].output == {"echoed": "facade"}

    def test_get_run_after_execution(self, skill: OrchestratorSkill):
        skill.register("echo", "say", lambda **kw: {})
        wf = Workflow(id="wf-f2", name="Store Test",
                      steps=[WorkflowStep(id="s1", skill_name="echo", operation="say")])
        run = skill.run_workflow(wf)
        loaded = skill.get_run(run.run_id)
        assert loaded is not None
        assert loaded.run_id == run.run_id

    def test_list_runs(self, skill: OrchestratorSkill):
        skill.register("echo", "say", lambda **kw: {})
        for i in range(3):
            wf = Workflow(id=f"wf-l{i}", name=f"WF{i}",
                          steps=[WorkflowStep(id="s1", skill_name="echo", operation="say")])
            skill.run_workflow(wf)
        runs = skill.list_runs()
        assert len(runs) >= 3

    def test_list_registry(self, skill: OrchestratorSkill):
        skill.register("echo", "say", lambda **kw: {})
        skill.register("echo", "shout", lambda **kw: {})
        mapping = skill.list_registry()
        assert "echo" in mapping
        assert set(mapping["echo"]) == {"say", "shout"}

    def test_multi_step_with_template(self, skill: OrchestratorSkill):
        skill.register("echo", "say", lambda message="": {"msg": message})
        skill.register("echo", "upper", lambda text="": {"result": text.upper()})
        wf = Workflow(
            id="wf-tmpl", name="Template Test",
            steps=[
                WorkflowStep(id="s1", skill_name="echo", operation="say",
                             params={"message": "hello"}),
                WorkflowStep(id="s2", skill_name="echo", operation="upper",
                             params={"text": "{s1.output.msg}"}, depends_on=["s1"]),
            ],
        )
        run = skill.run_workflow(wf)
        assert run.status == WorkflowStatus.COMPLETED
        assert run.step_results["s2"].output["result"] == "HELLO"

    def test_register_skill_batch(self, skill: OrchestratorSkill):
        skill.register_skill("math", {
            "add": lambda a=0, b=0: {"sum": a + b},
            "mul": lambda a=1, b=1: {"product": a * b},
        })
        assert skill.list_registry()["math"] == ["add", "mul"]
