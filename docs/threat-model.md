# SentinelOps AI Security & Threat Model

## 1. Threat Landscape (OWASP Top 10 for LLMs)

Autonomous SRE and operations agents have direct or indirect access to high-privilege infrastructure APIs. A compromised or malfunctioning agent can trigger catastrophic cloud outages or leak sensitive customer data.

| OWASP LLM Threat | SentinelOps Threat Vector | SentinelOps Defense Architecture |
|---|---|---|
| **LLM01: Prompt Injection** | Malicious payloads placed inside system logs, user error messages, or exception traces to force the agent to execute unauthorized commands. | **Strict Boundary Isolation:** Logs and untrusted strings are formatted inside structured JSON payloads and never interpolated directly into raw prompt templates. Input sanitizers strip command escape characters. |
| **LLM02: Sensitive Information Disclosure** | Database credentials, API tokens, or customer PII exposed in diagnostic query outputs or logs. | **Pre-LLM Data Sanitization:** Regex-based credential scrubbers redact passwords, connection strings, and JWTs before context is passed to the LLM. |
| **LLM03: Supply Chain Vulnerabilities** | Malicious external MCP servers or compromised model weights. | **MCP Server Allowlisting & Pinning:** Only verified internal MCP servers with authenticated TLS certificates and cryptographic checksums are registered. |
| **LLM06: Excessive Agency** | An agent deciding autonomously to drop a database table or terminate all production compute instances. | **Deterministic Human-in-the-Loop Gates & Policy Engine:** LLM decisions are untrusted recommendations. Actions are classified by risk tier; any destructive mutation requires human authorization. |
| **LLM08: Vector and Embedding Weaknesses** | Poisoned runbooks in the knowledge base directing the agent to disable security firewalls during an incident. | **Role-Based Runbook Write Access:** Runbooks are stored as versioned immutable Git artifacts; vector collections are re-indexed only via signed CI/CD pipelines. |

## 2. Trust Boundaries

```
[ UNTRUSTED ZONE ]
External CloudWatch Alerts, Raw Pod Logs, Third-party Webhooks
       │
       ▼ (Sanitization & PII Redaction Boundary)
[ SEMI-TRUSTED ZONE ]
LLM Prompts, Agent Reasoning Scratchpad, Vector Embeddings
       │
       ▼ (Deterministic Policy & Human Approval Gate)
[ TRUSTED ZONE ]
AWS API Mutations, K8s kubectl execution, Production Database Changes
```
