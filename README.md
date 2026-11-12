# SentinelOps: Autonomous AI Operations & Incident Remediation Platform

SentinelOps is a production-grade, multi-agent AI incident remediation platform designed to investigate complex cloud infrastructure outages, correlate telemetry with runbooks and topological dependency graphs, coordinate specialist agents, and execute remediations with strict Human-in-the-Loop (HITL) authorization and least-privilege security.

---

## 📅 4-Week Engineering Roadmap

We follow a daily hands-on engineering methodology:  
**Theory & Literature → Implementation in Python → SentinelOps Integration → Automated Testing → Architectural Review.**

The complete 28-day roadmap and learning contract is documented in [FOUR_WEEK_PLAN.md](file:///Users/hadi/PycharmProjects/sentinelops/FOUR_WEEK_PLAN.md).

---

## 🚀 Current Status: Day 1

We are working through the program **day by day**. Each day has its own dedicated documentation guide, hands-on coding exercises, and automated test suite:

- **Active Guide:** [Day 01 — Transformer Architecture & LLM Internals](file:///Users/hadi/PycharmProjects/sentinelops/docs/DAY01_TRANSFORMER_ARCHITECTURE_AND_LLM_INTERNALS.md)
  - Focus: Self-attention mechanics, tokenization of cloud logs, embeddings, KV cache memory footprint, and hallucination diagnosis.
  - Video & Reading recommendations: Andrej Karpathy (Let's build GPT), 3Blue1Brown (Visualizing Attention), Umar Jamil (Attention is All You Need).
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

