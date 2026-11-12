# Runbook: RDS Aurora PostgreSQL Failover & Connection Saturation (RB-DB-001)

## Trigger Conditions
- Metric: `DatabaseConnections` > 95% of MaxCapacity for > 3 minutes.
- Metric: `CPUUtilization` = 100% on Aurora Primary DB Instance.
- Alert: `PostgreSQLLogErrors: FATAL: remaining connection slots are reserved for non-replication superuser connections`.

## Blast Radius
- Impacts Order Service, Payment Gateway, and Inventory Query Service.
- Secondary impact: Message queues back up (Dead Letter Queue threshold exceeded).

## Automated Diagnostic Steps
1. Verify Primary vs Replica replication lag in CloudWatch (`ReplicationLag` metric).
2. Query active queries from `pg_stat_activity` with duration > 30s.
3. Check for lock waits and transaction blocking chains (`pg_locks`).
4. Validate connection pooler (PgBouncer / AWS RDS Proxy) health.

## Remediation Policy
- Low Risk (Auto-authorized): Restart stalled PgBouncer containers to drop orphaned client sockets.
- High Risk (REQUIRES HUMAN OPERATOR APPROVAL):
  1. Trigger Aurora DB Cluster Failover to promotion-ready Read Replica in `az-2`.
  2. Kill long-running write query transactions older than 180 seconds.
