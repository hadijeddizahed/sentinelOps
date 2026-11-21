# Runbook: Kubernetes Pod CrashLoopBackOff & OOMKilled Mitigation (RB-K8S-002)

## Trigger Conditions
- Event: `BackOff` or `CrashLoopBackOff` in `production` namespace for > 2 minutes.
- Container termination state: `OOMKilled` with `exit_code: 137` (SIGKILL from Linux kernel cgroup memory limit).
- Metric: `container_memory_working_set_bytes` reaches 100% of pod memory limit.

## Blast Radius
- Impacts Payment Ingress Service and Checkout Webhook Workers.
- Increased 502/504 Gateway Timeouts at Application Load Balancer (ALB).

## Automated Diagnostic Steps
1. Fetch recent container logs using `fetch_pod_logs` and check for `OutOfMemoryException` or heap exhaustion prior to exit code 137.
2. Inspect pod spec resource limits (`resources.limits.memory`) versus historical 24-hour p99 memory consumption.
3. Verify if a recent deployment rollout introduced a memory leak.

## Remediation Policy
- Low Risk (Auto-authorized): Trigger graceful rollout restart of affected pod if caused by transient traffic spike.
- High Risk (REQUIRES HUMAN OPERATOR APPROVAL):
  1. Patch Kubernetes Deployment manifest to increase memory limit from `512Mi` to `1Gi`.
  2. Roll back deployment to previous stable ReplicaSet revision.