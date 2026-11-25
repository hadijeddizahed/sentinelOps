# SentinelOps: Autonomous AI Operations & Incident Remediation Platform

SentinelOps is a production-grade, multi-agent AI incident remediation platform designed to investigate complex cloud infrastructure outages, correlate telemetry with runbooks and topological dependency graphs, coordinate specialist agents, and execute remediations with strict Human-in-the-Loop (HITL) authorization and least-privilege security.

---

## 📅 4-Week Engineering Roadmap

We follow a daily hands-on engineering methodology:  
**Theory & Literature → Implementation in Python → SentinelOps Integration → Automated Testing → Architectural Review.**

The complete 28-day roadmap and learning contract is documented in [FOUR_WEEK_PLAN.md](file:///Users/hadi/PycharmProjects/sentinelops/FOUR_WEEK_PLAN.md).

---

## 🚀 Current Status: Day 5

We work through the program **day by day**. Each day has its own dedicated documentation guide, hands-on coding exercises, and automated test suite:

- **Active Guide:** [Day 05 — Advanced RAG Architecture: Hybrid Search & Reranking](file:///Users/hadi/PycharmProjects/sentinelops/docs/DAY05_ADVANCED_RAG_HYBRID_AND_RERANKING.md)
  - Focus: Sparse BM25 (`rank-bm25`) + Dense Qdrant vector search, Reciprocal Rank Fusion (RRF), query expansion, and Stage-2 Cross-Encoder reranking.
  - Video & Reading: James Briggs (Hybrid Search & RRF), Nils Reimers (Bi-Encoders vs Cross-Encoders), Qdrant (Hybrid Sparse & Dense Search).
- **Completed:** 
  - [Day 01 — Transformer Architecture & LLM Internals](file:///Users/hadi/PycharmProjects/sentinelops/docs/DAY01_TRANSFORMER_ARCHITECTURE_AND_LLM_INTERNALS.md)
  - [Day 02 — Advanced Prompting & Structured Outputs](file:///Users/hadi/PycharmProjects/sentinelops/docs/DAY02_ADVANCED_PROMPTING_AND_STRUCTURED_OUTPUTS.md)
  - [Day 03 — Function Calling & Advanced Tool Use](file:///Users/hadi/PycharmProjects/sentinelops/docs/DAY03_FUNCTION_CALLING_AND_TOOL_USE.md)
  - [Day 04 — Embeddings & Vector Databases](file:///Users/hadi/PycharmProjects/sentinelops/docs/DAY04_EMBEDDINGS_AND_VECTOR_DATABASES.md)
- **Core Architecture:** [docs/architecture.md](file:///Users/hadi/PycharmProjects/sentinelops/docs/architecture.md)
- **Security & Threat Model:** [docs/threat-model.md](file:///Users/hadi/PycharmProjects/sentinelops/docs/threat-model.md)
- **Architecture Decisions:** [ADR 0001: LangGraph Selection](file:///Users/hadi/PycharmProjects/sentinelops/docs/adr/0001_agent_orchestration_framework.md)

---

## 🛠️ Repository Layout

```
sentinelops/
├── pyproject.toml              # Dependencies & test config
├── docker-compose.yml          # Local Qdrant, Postgres & Prometheus
├── FOUR_WEEK_PLAN.md           # Master 28-day engineering roadmap
├── README.md
├── app/
│   ├── config.py               # Pydantic Settings
│   ├── api/routes/             # FastAPI endpoints (incidents, health)
│   ├── agents/                 # Supervisor, Network, DB, Security agents
│   ├── graph/                  # LangGraph StateGraph, nodes, edges, state
│   ├── rag/                    # Embeddings, BM25, Qdrant, reranking, graph
│   ├── mcp/                    # FastMCP diagnostic servers and client
│   ├── tools/                  # Scoped infrastructure & AWS tools
│   ├── security/               # Sandboxing, policy engine, permissions
│   └── workers/                # Async incident processing workers
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Workflow and state tests
│   ├── evaluation/             # Retrieval & benchmark tests
│   └── adversarial/            # Prompt injection & security tests
├── infrastructure/             # Docker, Kubernetes, and Prometheus manifests
├── data/
│   ├── runbooks/               # Structured incident runbooks (Markdown)
│   └── incidents/              # Simulated incidents & golden dataset
└── docs/                       # Daily documentation guides and ADRs
```
