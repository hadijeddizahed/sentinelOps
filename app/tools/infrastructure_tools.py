from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from app.tools.registry import ToolRegistry

# Default global registry for infrastructure tools
infra_registry = ToolRegistry()


# ==============================================================================
# TOOL 1: CloudWatch Telemetry Metrics
# ==============================================================================
class QueryCloudWatchMetricsArgs(BaseModel):
    """Arguments for querying cloud telemetry metrics."""
    namespace: Literal["AWS/RDS", "AWS/ECS", "AWS/ApplicationELB", "AWS/NATGateway"] = Field(
        description="AWS metric namespace"
    )
    metric_name: Literal[
        "CPUUtilization",
        "DatabaseConnections",
        "FreeableMemory",
        "HTTPCode_Target_5XX_Count",
        "BytesOut"
    ] = Field(description="CloudWatch metric name")
    resource_id: str = Field(min_length=3, description="Resource identifier (e.g. prod-orders-cluster)")
    period_minutes: int = Field(default=5, ge=1, le=60, description="Metric sampling duration in minutes")


@infra_registry.register(name="query_cloudwatch_metrics", scope="READ_ONLY")
def query_cloudwatch_metrics(args: QueryCloudWatchMetricsArgs) -> Dict[str, Any]:
    """Query CloudWatch telemetry metrics for an infrastructure resource."""
    # Simulated metrics engine grounded in realistic incident data
    if "orders" in args.resource_id:
        if args.metric_name == "DatabaseConnections":
            return {
                "resource_id": args.resource_id,
                "metric": "DatabaseConnections",
                "current_value": 498,
                "max_threshold": 500,
                "unit": "Count",
                "status": "CRITICAL_SATURATION"
            }
        elif args.metric_name == "CPUUtilization":
            return {
                "resource_id": args.resource_id,
                "metric": "CPUUtilization",
                "current_value": 94.2,
                "unit": "Percent",
                "status": "WARNING"
            }

    return {
        "resource_id": args.resource_id,
        "metric": args.metric_name,
        "current_value": 24.5,
        "unit": "Average",
        "status": "HEALTHY"
    }


# ==============================================================================
# TOOL 2: Kubernetes Pod Log Inspector
# ==============================================================================
class FetchPodLogsArgs(BaseModel):
    """Arguments for retrieving container logs from Kubernetes."""
    namespace: str = Field(default="production", min_length=2, description="K8s namespace")
    pod_name: str = Field(min_length=3, description="Target pod name or prefix")
    tail_lines: int = Field(default=50, ge=1, le=200, description="Number of recent log lines")
    filter_errors_only: bool = Field(default=True, description="Filter for ERROR, FATAL, and Exception lines")


@infra_registry.register(name="fetch_pod_logs", scope="READ_ONLY")
def fetch_pod_logs(args: FetchPodLogsArgs) -> str:
    """Fetch container logs and stack traces from a Kubernetes pod."""
    if "payment" in args.pod_name:
        return (
            "[2026-11-16 20:55:01] INFO  payment-ingress: Listening on :8080\n"
            "[2026-11-16 20:56:12] ERROR payment-ingress: DBConnectionError: connection pool exhausted (timeout 30s)\n"
            "[2026-11-16 20:56:14] FATAL payment-ingress: System.OutOfMemoryException: Container terminated exit_code:137 (OOMKilled)"
        )
    return f"Logs from {args.pod_name} ({args.namespace}): All services operating within SLA parameters."


# ==============================================================================
# TOOL 3: Database Connection Pool Diagnostics
# ==============================================================================
class CheckDatabasePoolArgs(BaseModel):
    """Arguments for deep database connection pool diagnostics."""
    cluster_id: str = Field(min_length=3, description="RDS Cluster Identifier")
    inspect_target: Literal["connection_slots", "long_running_queries", "lock_waits"] = Field(
        description="Target diagnostic area to inspect"
    )


@infra_registry.register(name="check_database_pool", scope="READ_ONLY")
def check_database_pool(args: CheckDatabasePoolArgs) -> Dict[str, Any]:
    """Inspect active PostgreSQL transactions, lock chains, and connection allocation."""
    if args.inspect_target == "connection_slots":
        return {
            "cluster_id": args.cluster_id,
            "total_slots": 500,
            "active_connections": 498,
            "idle_in_transaction": 342,  # Orphaned client connections
            "waiting_clients": 87,
            "root_cause_indicator": "High count of 'idle in transaction' connections holding open sockets"
        }
    elif args.inspect_target == "lock_waits":
        return {
            "cluster_id": args.cluster_id,
            "blocked_transactions_count": 12,
            "root_blocking_pid": 89412,
            "blocking_query": "UPDATE orders SET status = 'PROCESSING' WHERE customer_id = 9921"
        }
    return {"cluster_id": args.cluster_id, "status": "Normal query execution"}


# ==============================================================================
# TOOL 4: Mutating Action (Requires Approval)
# ==============================================================================
class RestartPodArgs(BaseModel):
    """Arguments for restarting a Kubernetes workload."""
    namespace: str = Field(min_length=2)
    pod_name: str = Field(min_length=3)
    reason: str = Field(min_length=10, description="Audit justification for restarting the pod")


@infra_registry.register(name="restart_kubernetes_pod", scope="MUTATING")
def restart_kubernetes_pod(args: RestartPodArgs) -> Dict[str, Any]:
    """Trigger graceful restart of a Kubernetes pod (MUTATING ACTION)."""
    return {
        "status": "RESTARTED",
        "pod_name": args.pod_name,
        "namespace": args.namespace,
        "reason": args.reason,
        "message": f"Successfully initiated rollout restart for {args.pod_name}."
    }