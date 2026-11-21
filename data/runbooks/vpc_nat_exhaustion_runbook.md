# Runbook: AWS VPC NAT Gateway Port Exhaustion & Packet Drop (RB-VPC-003)

## Trigger Conditions
- Metric: `ErrorPortAllocation` > 0 on AWS NAT Gateway in CloudWatch.
- Metric: `PacketsDropCount` spiking above 500 packets/minute.
- Symptom: Outbound HTTPS calls to external payment processors (Stripe / Adyen) failing with `ConnectTimeoutError`.

## Blast Radius
- Impacts all private subnet microservices making outbound third-party API calls.
- Payment authorization and external fraud verification degraded.

## Automated Diagnostic Steps
1. Query CloudWatch metrics for `ActiveConnectionCount` and `ErrorPortAllocation` on the NAT Gateway.
2. Inspect VPC Flow Logs to identify which internal private IP is opening excessive ephemeral TCP connections without connection pooling.
3. Verify route table associations for private subnets across availability zones.

## Remediation Policy
- Low Risk (Auto-authorized): Enable HTTP keep-alive connection pooling flag on offending egress worker service.
- High Risk (REQUIRES HUMAN OPERATOR APPROVAL):
  1. Associate a secondary Elastic IP (EIP) to the NAT Gateway to double available SNAT ports (up to 110,000 ports).
  2. Split private subnet route tables across multi-AZ NAT Gateways.