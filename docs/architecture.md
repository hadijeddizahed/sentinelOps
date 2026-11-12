# SentinelOps System Architecture

## 1. High-Level System Architecture Diagram

```
[ Monitoring Alerts (CloudWatch / SQS / Webhook) ]
                       │
                       ▼
         [ FastAPI Ingestion Gateway ]
                       │
                       ▼
        [ LangGraph Incident Orchestrator ]
         ┌──────────────────────────────────────────────┐
         │                                              │
         │  [ Supervisor Agent ]                        │
         │         │                                    │
         │         ├───► [ Network Specialist Agent ]   │
         │         ├───► [ Database Specialist Agent ]  │
         │         └───► [ Security Specialist Agent ]  │
         │                                              │
         │  [ Hybrid RAG + Knowledge Graph Engine ]     │
         │    - Qdrant (Dense Vectors)                  │
         │    - BM25 (Sparse Error Codes)               │
         │    - NetworkX (Infra Blast Radius Graph)     │
         │                                              │
         │  [ Human-In-The-Loop Approval Gate ]         │
         │    - Risk Policy Engine                      │
         │    - Graph Checkpointing (Postgres/Sqlite)   │
         │    - Operator Decision Interface             │
         │                                              │
         │  [ MCP Tool Execution Sandbox ]              │
         │    - FastMCP Diagnostic Server               │
         │    - Scoped Least-Privilege IAM              │
         │    - Command Allowlist Runner                │
         └──────────────────────────────────────────────┘
                       │
                       ▼
      [ Prometheus Metrics & LangSmith Traces ]
```

## 2. Component Breakdown

### A. Graph Orchestrator (LangGraph)
Uses a unified state machine defined in `app/graph/state.py`.
- **State Schema:** Carries incident alert payloads, accumulating findings (`Annotated[List[Finding], operator.add]`), blast radius nodes, remediation proposals, and execution logs.
- **Checkpointing:** State snapshots are committed after every node transition, enabling pause-and-resume for human operator review and zero-data-loss crash recovery.

### B. Hybrid RAG & Knowledge Graph
- **Dense Vector Search:** Encodes incident descriptions and runbooks using `sentence-transformers/all-MiniLM-L6-v2` stored in Qdrant.
- **Sparse BM25 Search:** Handles verbatim technical strings like exception traces (`ORA-00001`, `K8S_OOM_137`).
- **Reciprocal Rank Fusion (RRF):** Fuses sparse and dense result rankings:
  $$RRF(d) = \sum_{m \in M} rac{1}{60 + r_m(d)}$$
- **NetworkX Topology Graph:** Computes directed reachability from the affected node to identify affected downstream microservices.

### C. Multi-Agent Specialist Squad
- **Supervisor:** Performs initial alert decomposition and fans out investigative tasks.
- **Database Agent:** Inspects active lock queues, connection counts, and transaction ages.
- **Network Agent:** Checks DNS resolution, VPC routing, and NAT Gateway packet drops.
- **Security Agent:** Verifies IAM audit logs (CloudTrail) to ensure the anomaly is not an active security breach.

### D. MCP Diagnostic & Remediation Sandbox
Diagnostic operations are accessed via Model Context Protocol (MCP) clients connecting to a dedicated FastMCP server. Remediation commands pass through a deterministic security policy check before touching infrastructure.
