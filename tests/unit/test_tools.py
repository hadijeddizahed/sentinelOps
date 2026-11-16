from pydantic import BaseModel
from app.tools.registry import ToolRegistry
from app.tools.infrastructure_tools import infra_registry


def test_tool_schema_generation():
    """Verify all registered tools export compliant function calling JSON schemas."""
    schemas = infra_registry.get_tool_schemas()
    assert len(schemas) == 4

    tool_names = {s["function"]["name"] for s in schemas}
    assert tool_names == {
        "query_cloudwatch_metrics",
        "fetch_pod_logs",
        "check_database_pool",
        "restart_kubernetes_pod",
    }

    # Verify parameters schema structure
    cw_schema = next(s for s in schemas if s["function"]["name"] == "query_cloudwatch_metrics")
    assert "properties" in cw_schema["function"]["parameters"]
    assert "namespace" in cw_schema["function"]["parameters"]["properties"]


def test_read_only_tool_execution_success():
    """Verify valid diagnostic tool call executes and formats observation."""
    res = infra_registry.execute(
        "query_cloudwatch_metrics",
        {
            "namespace": "AWS/RDS",
            "metric_name": "DatabaseConnections",
            "resource_id": "prod-orders-cluster",
            "period_minutes": 5,
        },
    )
    assert res.status == "SUCCESS"
    assert res.scope == "READ_ONLY"
    assert res.data["current_value"] == 498
    assert res.data["status"] == "CRITICAL_SATURATION"
    assert "Observation from query_cloudwatch_metrics" in res.observation


def test_invalid_arguments_return_reflection_observation():
    """Verify schema violations return structured error observations without raising exceptions."""
    res = infra_registry.execute(
        "query_cloudwatch_metrics",
        {
            "namespace": "AWS/InvalidService",  # Invalid Literal
            "metric_name": "DatabaseConnections",
            "resource_id": "db",  # Too short (min_length=3)
        },
    )
    assert res.status == "ERROR"
    assert "[Schema Validation Error]" in res.observation
    assert "namespace" in res.observation
    assert "resource_id" in res.observation


def test_unknown_hallucinated_tool_handled_gracefully():
    """Verify calling a non-existent tool returns helpful error listing available tools."""
    res = infra_registry.execute("delete_production_database", {"confirm": True})
    assert res.status == "ERROR"
    assert "not found" in res.observation
    assert "query_cloudwatch_metrics" in res.observation


def test_mutating_tool_blocked_without_permission():
    """Verify MUTATING tools are blocked by default and allowed only when authorized."""
    args = {
        "namespace": "production",
        "pod_name": "payment-ingress-7d4b",
        "reason": "Mitigate OOMKilled container crashloop",
    }

    # 1. Blocked when allow_mutations=False (default)
    denied_res = infra_registry.execute("restart_kubernetes_pod", args, allow_mutations=False)
    assert denied_res.status == "PERMISSION_DENIED"
    assert denied_res.scope == "MUTATING"
    assert "[Permission Denied]" in denied_res.observation

    # 2. Allowed when allow_mutations=True (after human approval)
    allowed_res = infra_registry.execute("restart_kubernetes_pod", args, allow_mutations=True)
    assert allowed_res.status == "SUCCESS"
    assert allowed_res.data["status"] == "RESTARTED"


def test_runtime_exception_caught_as_observation():
    """Verify unexpected tool exceptions are caught and turned into agent observations."""
    custom_registry = ToolRegistry()

    class PingArgs(BaseModel):
        host: str

    @custom_registry.register(name="failing_network_ping", scope="READ_ONLY")
    def failing_network_ping(args: PingArgs) -> str:
        """Simulate a network timeout exception."""
        raise ConnectionError(f"Timeout connecting to gateway {args.host} on port 443")

    res = custom_registry.execute("failing_network_ping", {"host": "10.0.1.25"})
    assert res.status == "ERROR"
    assert "[API Runtime Error]" in res.observation
    assert "Timeout connecting to gateway 10.0.1.25" in res.observation