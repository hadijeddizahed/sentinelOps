# ADR 0001: Selection of LangGraph as Multi-Agent Orchestration Framework

## Status
Accepted

## Context
SentinelOps requires orchestrating multiple autonomous diagnostic agents, maintaining complex investigation state across multi-step triage workflows, pausing for human operator approval, and recovering deterministically from transient system failures.

We evaluated three potential orchestration frameworks:
1. **LangGraph (LangChain)**
2. **CrewAI**
3. **AutoGen (Microsoft)**

## Decision Matrix

| Requirement | LangGraph | CrewAI | AutoGen |
|---|---|---|---|
| **Deterministic State Machine (Cycles & Branches)** | **Excellent (Explicit Graph)** | Poor (Roleplay abstraction) | Moderate (Conversational) |
| **Human-in-the-loop (Interrupt / Resume)** | **Native (`interrupt()`)** | Complex Workarounds | Scripted Pause |
| **Built-in Durable Checkpointing** | **Native (Postgres/Sqlite)** | Limited | External |
| **Parallel Fan-out / Fan-in (`asyncio`)** | **Native (Fork/Join nodes)** | Sequential by default | Chat-turn based |
| **Strict Typed Schemas** | **Native (Pydantic v2)** | Pydantic supported | Unstructured messages |

## Decision
We select **LangGraph** as the primary orchestration engine for SentinelOps. Its graph-theoretic representation of state transitions provides the deterministic control, checkpointing, and interrupt capabilities necessary for enterprise reliability.
