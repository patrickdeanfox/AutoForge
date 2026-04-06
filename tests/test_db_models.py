"""Unit tests for AutoForge SQLAlchemy ORM models.

These tests exercise model instantiation, default values, and __repr__
without requiring a live database connection.
"""

from db.models import AgentRun, CostRecord, HumanGate, Project

# ============================================================
# PROJECT TESTS
# ============================================================


class TestProject:
    """Tests for the Project model."""

    def test_project_can_be_instantiated_with_required_fields(self) -> None:
        """Project accepts all required fields and stores them correctly."""
        project = Project(
            project_id="customer-etl-pipeline",
            name="Customer ETL Pipeline",
            client_name="Acme Corp",
        )
        assert project.project_id == "customer-etl-pipeline"
        assert project.name == "Customer ETL Pipeline"
        assert project.client_name == "Acme Corp"

    def test_project_status_default_is_intake(self) -> None:
        """Project.status defaults to 'intake' when not explicitly set."""
        project = Project(
            project_id="test-project",
            name="Test Project",
            client_name="Test Client",
        )
        assert project.status == "intake"

    def test_project_optional_fields_default_to_none(self) -> None:
        """Project optional fields (manifest_path, github_repo, approved_at) default to None."""
        project = Project(
            project_id="minimal-project",
            name="Minimal",
            client_name="Client",
        )
        assert project.manifest_path is None
        assert project.github_repo is None
        assert project.approved_at is None

    def test_project_repr_returns_string(self) -> None:
        """Project.__repr__ returns a non-empty string."""
        project = Project(
            project_id="repr-test",
            name="Repr Test",
            client_name="Client",
        )
        result = repr(project)
        assert isinstance(result, str)
        assert "repr-test" in result

    def test_project_accepts_all_status_values(self) -> None:
        """Project accepts all valid status strings without raising errors."""
        valid_statuses = [
            "intake",
            "knowledge_building",
            "planning",
            "execution",
            "qa",
            "complete",
            "archived",
        ]
        for status in valid_statuses:
            project = Project(
                project_id=f"proj-{status}",
                name="Test",
                client_name="Client",
                status=status,
            )
            assert project.status == status


# ============================================================
# AGENT RUN TESTS
# ============================================================


class TestAgentRun:
    """Tests for the AgentRun model."""

    def test_agent_run_can_be_instantiated_with_required_fields(self) -> None:
        """AgentRun accepts all required fields and stores them correctly."""
        run = AgentRun(
            run_id="run-abc123",
            project_id="customer-etl-pipeline",
            agent_name="coder-agent",
        )
        assert run.run_id == "run-abc123"
        assert run.project_id == "customer-etl-pipeline"
        assert run.agent_name == "coder-agent"

    def test_agent_run_status_default_is_running(self) -> None:
        """AgentRun.status defaults to 'running' when not explicitly set."""
        run = AgentRun(
            run_id="run-status-test",
            project_id="proj-1",
            agent_name="debug-agent",
        )
        assert run.status == "running"

    def test_agent_run_tokens_default_to_zero(self) -> None:
        """AgentRun.tokens_in and tokens_out default to 0."""
        run = AgentRun(
            run_id="run-tokens-test",
            project_id="proj-1",
            agent_name="qa-agent",
        )
        assert run.tokens_in == 0
        assert run.tokens_out == 0

    def test_agent_run_run_metadata_defaults_to_empty_dict(self) -> None:
        """AgentRun.run_metadata defaults to an empty dict."""
        run = AgentRun(
            run_id="run-meta-test",
            project_id="proj-1",
            agent_name="planner-agent",
        )
        assert run.run_metadata == {}

    def test_agent_run_optional_fields_default_to_none(self) -> None:
        """AgentRun nullable fields default to None when not provided."""
        run = AgentRun(
            run_id="run-nullable-test",
            project_id="proj-1",
            agent_name="refactor-agent",
        )
        assert run.issue_id is None
        assert run.branch is None
        assert run.completed_at is None
        assert run.duration_ms is None
        assert run.model is None
        assert run.error_message is None

    def test_agent_run_repr_returns_string(self) -> None:
        """AgentRun.__repr__ returns a non-empty string containing key fields."""
        run = AgentRun(
            run_id="run-repr-test",
            project_id="proj-1",
            agent_name="coder-agent",
        )
        result = repr(run)
        assert isinstance(result, str)
        assert "run-repr-test" in result
        assert "coder-agent" in result

    def test_agent_run_accepts_all_status_values(self) -> None:
        """AgentRun accepts all valid status strings without raising errors."""
        valid_statuses = ["running", "success", "failed", "escalated", "cancelled"]
        for status in valid_statuses:
            run = AgentRun(
                run_id=f"run-{status}",
                project_id="proj-1",
                agent_name="test-agent",
                status=status,
            )
            assert run.status == status


# ============================================================
# COST RECORD TESTS
# ============================================================


class TestCostRecord:
    """Tests for the CostRecord model."""

    def test_cost_record_can_be_instantiated_with_required_fields(self) -> None:
        """CostRecord accepts all required fields and stores them correctly."""
        record = CostRecord(
            run_id="run-abc123",
            project_id="customer-etl-pipeline",
            model="claude-opus-4-6",
            tokens_in=1000,
            tokens_out=250,
            cost_usd="0.003750",
        )
        assert record.run_id == "run-abc123"
        assert record.project_id == "customer-etl-pipeline"
        assert record.model == "claude-opus-4-6"
        assert record.tokens_in == 1000
        assert record.tokens_out == 250

    def test_cost_record_repr_returns_string(self) -> None:
        """CostRecord.__repr__ returns a non-empty string containing key fields."""
        record = CostRecord(
            run_id="run-repr-cost",
            project_id="proj-1",
            model="claude-sonnet-4-6",
            tokens_in=500,
            tokens_out=100,
            cost_usd="0.001500",
        )
        result = repr(record)
        assert isinstance(result, str)
        assert "run-repr-cost" in result
        assert "claude-sonnet-4-6" in result


# ============================================================
# HUMAN GATE TESTS
# ============================================================


class TestHumanGate:
    """Tests for the HumanGate model."""

    def test_human_gate_can_be_instantiated_with_required_fields(self) -> None:
        """HumanGate accepts all required fields and stores them correctly."""
        gate = HumanGate(
            gate_id="gate-xyz789",
            project_id="customer-etl-pipeline",
            gate_type="decision_needed",
            description="Choose between FastAPI and Flask for the service layer.",
        )
        assert gate.gate_id == "gate-xyz789"
        assert gate.project_id == "customer-etl-pipeline"
        assert gate.gate_type == "decision_needed"
        assert "FastAPI" in gate.description

    def test_human_gate_status_default_is_pending(self) -> None:
        """HumanGate.status defaults to 'pending' when not explicitly set."""
        gate = HumanGate(
            gate_id="gate-status-test",
            project_id="proj-1",
            gate_type="spec_approval",
            description="Approve the project spec.",
        )
        assert gate.status == "pending"

    def test_human_gate_optional_fields_default_to_none(self) -> None:
        """HumanGate nullable fields default to None when not provided."""
        gate = HumanGate(
            gate_id="gate-nullable-test",
            project_id="proj-1",
            gate_type="needs_human",
            description="Agent is stuck after 3 attempts.",
        )
        assert gate.github_issue_url is None
        assert gate.telegram_message_id is None
        assert gate.resolved_at is None
        assert gate.resolved_by is None

    def test_human_gate_repr_returns_string(self) -> None:
        """HumanGate.__repr__ returns a non-empty string containing key fields."""
        gate = HumanGate(
            gate_id="gate-repr-test",
            project_id="proj-1",
            gate_type="pr_merge",
            description="Merge PR #42.",
        )
        result = repr(gate)
        assert isinstance(result, str)
        assert "gate-repr-test" in result
        assert "pr_merge" in result

    def test_human_gate_accepts_all_status_values(self) -> None:
        """HumanGate accepts all valid status strings without raising errors."""
        valid_statuses = ["pending", "approved", "rejected", "expired"]
        for status in valid_statuses:
            gate = HumanGate(
                gate_id=f"gate-{status}",
                project_id="proj-1",
                gate_type="manifest_lock",
                description=f"Gate with status {status}.",
                status=status,
            )
            assert gate.status == status

    def test_human_gate_accepts_all_gate_type_values(self) -> None:
        """HumanGate accepts all documented gate_type strings without raising errors."""
        valid_gate_types = [
            "spec_approval",
            "manifest_lock",
            "pr_merge",
            "decision_needed",
            "needs_human",
        ]
        for gate_type in valid_gate_types:
            gate = HumanGate(
                gate_id=f"gate-type-{gate_type}",
                project_id="proj-1",
                gate_type=gate_type,
                description=f"Gate of type {gate_type}.",
            )
            assert gate.gate_type == gate_type
