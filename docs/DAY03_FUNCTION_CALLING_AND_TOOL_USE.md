# Day 03: Function Calling & Advanced Tool Use

**Phase:** Week 1 — Advanced LLM Engineering & Knowledge Intelligence  
**Focus:** Typed Tool Declarations, Dynamic Tool Registry, Argument Validation, Error Reflection, and Safety Scopes

---

## 1. Executive Summary & Why This Matters

An LLM that cannot invoke external APIs is merely a conversational text engine. To triage and resolve infrastructure outages, an operations agent must inspect live metrics, query database connection pools, read Kubernetes pod logs, and trigger safe mitigations.

However, unconstrained tool execution in production infrastructure is hazardous:
1. If an LLM hallucinates an invalid CLI parameter or non-existent AWS region, an unhandled exception will crash the agent.
2. If an API returns a `429 Too Many Requests` or `500 Internal Server Error`, the agent must not crash—it must receive the error as an **Observation**, reflect on it, and adjust its strategy.
3. If an agent executes destructive mutations (e.g. `reboot_db_instance`) without authorization or validation, it can turn a minor glitch into a company-wide disaster.

Today, you will build a type-safe **Tool Registry and Dispatch Engine** that validates arguments with Pydantic v2, enforces safety scopes (Read-Only vs. Mutating), captures errors gracefully into agent observations, and provides structured OpenAPI schemas to the LLM.

---

## 2. Learning Objectives

By the end of today, you will understand and be able to:
1. **Define typed tools using Pydantic schemas:** Auto-generate compliant JSON Schema / OpenAPI function definitions from Python type hints and docstrings.
2. **Build a central `ToolRegistry`:** Implement dynamic registration, schema generation, argument validation, and execution dispatching.
3. **Enforce Safety Scopes (Read-Only vs. Mutating):** Classify tools by risk tier (`READ_ONLY`, `DIAGNOSTIC`, `MUTATING`) so agents cannot execute dangerous actions without explicit policy permission.
4. **Implement Tool Reflection & Error Recovery:** Catch runtime exceptions from real or simulated cloud APIs and format them into structured `Observation` payloads, enabling the agent to self-correct instead of crashing.
5. **Prepare for LangGraph & MCP:** Design tools with standard interfaces ready to be wired into LangGraph nodes (Week 2) and Model Context Protocol servers (Week 3).

---

## 3. Technical Deep-Dive

### A. The Tool Execution Lifecycle

```
[ LLM Context ] ─── Receives user prompt + Available Tool Schemas
       │
       ▼
[ Tool Call Emitted ] ─── E.g. {"name": "query_cloudwatch_metrics", "arguments": {"metric": "CPUUtilization"}}
       │
       ▼
[ Tool Registry ] ─── Intercepts call
       ├── 1. Validates arguments against Pydantic schema
       ├── 2. Checks permission scope (READ_ONLY vs MUTATING)
       └── 3. Invokes underlying Python function in try/except block
       │
       ├─────────────────────────────────┐
       ▼ (Success)                       ▼ (Exception / API Failure)
[ ToolResult ]                     [ Structured Error Observation ]
"CPUUtilization is 98.4%"          "Error: Resource 'prod-db' not found in us-east-1"
       │                                 │
       └────────────────┬────────────────┘
                        ▼
               [ Injected as Observation into LLM Message History ]
                        │
                        ▼
               [ LLM Next Thought / Action ]
```

### B. Tool Reflection: Turning Exceptions into Observations
When a tool fails:
- **Wrong Approach:** Let the Python exception bubble up and kill the process.
- **Correct Production Approach:** Catch the exception, wrap it in a typed `ToolResult(status="ERROR", message="...")`, and return it to the LLM. The agent's prompt instructs:
  > *"Observation: Error calling query_rds_connections. The cluster identifier 'orders-db-01' does not exist in region us-east-1. Available clusters: ['orders-db-primary', 'orders-db-replica']."*
  The LLM reasons: *"I mistyped the cluster identifier; let me retry using 'orders-db-primary'."*

---

## 4. Curated Learning Resources

### High-Impact YouTube Lectures
1. **Harrison Chase (LangChain) — "Tool Calling and Structured Outputs with LangChain"**
   - **URL:** https://www.youtube.com/watch?v=0k3F_QvPqE8
   - **Channel:** LangChain
   - *Why watch:* Authoritative overview of function calling mechanics, schema translation, and how orchestrators handle dispatch.
2. **James Briggs — "How LLM Function Calling Actually Works"**
   - **URL:** https://www.youtube.com/watch?v=aqdUShDUa70
   - **Channel:** James Briggs
   - *Why watch:* Code-level breakdown of tool schemas, OpenAI/Anthropic tool formats, and building manual tool calling loops in Python.
3. **Sam Witteveen — "Tools and Function Calling in Agentic Workflows"**
   - **URL:** https://www.youtube.com/watch?v=mGzH7y1gJ_4
   - **Channel:** Sam Witteveen
   - *Why watch:* Deep dive into multi-tool reasoning, avoiding loop traps, and structuring tool outputs.

### Official Documentation
- **LangChain Tool Calling Guide:** https://python.langchain.com/docs/how_to/function_calling/
- **Anthropic Claude Tool Use Documentation:** https://docs.anthropic.com/en/docs/build-with-claude/tool-use
- **OpenAI Function Calling Guide:** https://platform.openai.com/docs/guides/function-calling

---

## 5. Hands-on Guided Exercise (Conceptual Prototype)

Here is how typed tool registration, validation, and error recovery work in pure Python:

```python
from pydantic import BaseModel, Field
from typing import Callable, Dict, Any, Type, Literal

class ToolRegistryDemo:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Type[BaseModel]] = {}
        self._scopes: Dict[str, str] = {}

    def register(self, name: str, schema: Type[BaseModel], scope: Literal["READ_ONLY", "MUTATING"] = "READ_ONLY"):
        def decorator(func: Callable):
            self._tools[name] = func
            self._schemas[name] = schema
            self._scopes[name] = scope
            return func
        return decorator

    def execute(self, tool_name: str, raw_args: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name not in self._tools:
            return {"status": "ERROR", "error": f"Tool '{tool_name}' is not registered."}
        try:
            # Pydantic validates input arguments
            validated_args = self._schemas[tool_name].model_validate(raw_args)
            result = self._tools[tool_name](**validated_args.model_dump())
            return {"status": "SUCCESS", "result": result, "scope": self._scopes[tool_name]}
        except Exception as exc:
            # Wrap error as observation for LLM reflection
            return {"status": "ERROR", "error": str(exc), "scope": self._scopes[tool_name]}

registry = ToolRegistryDemo()

class QueryRDSArgs(BaseModel):
    cluster_id: str = Field(min_length=3, description="RDS DB Cluster Identifier")
    metric: Literal["DatabaseConnections", "CPUUtilization", "FreeableMemory"]

@registry.register("query_rds_metric", QueryRDSArgs, scope="READ_ONLY")
def query_rds_metric(cluster_id: str, metric: str) -> str:
    if "prod" not in cluster_id:
        raise ValueError(f"Cluster '{cluster_id}' not found in current VPC.")
    return f"Metric {metric} for {cluster_id} is currently 485 (Max: 500)."

if __name__ == "__main__":
    # Test valid invocation
    print(registry.execute("query_rds_metric", {"cluster_id": "prod-orders", "metric": "DatabaseConnections"}))
    # Test validation error (handled cleanly as observation)
    print(registry.execute("query_rds_metric", {"cluster_id": "staging-db", "metric": "DatabaseConnections"}))
```

---

## 6. SentinelOps Core Implementation Plan (What We Will Code)

When we begin the coding phase, we will implement this step-by-step:
- **Step 1:** Define the core `ToolRegistry`, typed `ToolResult`, and safety permission scopes in `app/tools/registry.py`.
- **Step 2:** Build production SRE diagnostic tools in `app/tools/infrastructure_tools.py` (`query_cloudwatch_metric`, `fetch_pod_logs`, `check_connection_pool`).
- **Step 3:** Write comprehensive automated unit tests in `tests/unit/test_tools.py` verifying schema validation, scope enforcement, and reflection error handling.

---

## 7. Exit Criteria Checklist

- [ ] Studied the function calling lifecycle and schema generation.
- [ ] Understand why exceptions must be caught and turned into `Observation` payloads.
- [ ] Understand the safety boundary between `READ_ONLY` and `MUTATING` tools.
- [ ] Ready to implement the SentinelOps Tool Registry step-by-step.

---

## 8. Senior AI Engineer Interview Prep

**Q1: How do you prevent an agent from getting trapped in an infinite tool-calling loop when an API fails?**  
*Model Answer:*  
In production agent architectures, we implement three layers of loop prevention:
1. **Hard Iteration Caps:** A maximum iteration counter in graph state (e.g., `MAX_STEPS = 10`). Reaching the cap routes execution to an escalation node.
2. **Action Deduplication Hashing:** We compute a hash of the `(tool_name, arguments_json)` tuple for each turn. If an agent attempts to execute the exact same tool with the exact same arguments three times consecutively and receives errors, the orchestrator overrides the LLM and forces an alternative branch.
3. **Reflection Error Prompts:** The error observation returned to the LLM explicitly states: *"You have failed 2 attempts with this tool. Do NOT repeat the same call. Formulate an alternative hypothesis or request human assistance."*

**Q2: What is the security risk of exposing system commands (e.g. bash or shell) as agent tools, and how should infrastructure tools be restricted?**  
*Model Answer:*  
Exposing raw shell tools (`run_bash_command`) introduces critical vulnerability to **Indirect Prompt Injection**: an attacker can plant a malicious command in an error log or database record, which the LLM reads and executes with the application's credentials.  
Infrastructure tools must strictly adhere to the **Principle of Least Privilege**:
- Tools must be typed, specific functions (e.g., `restart_kubernetes_pod(namespace, pod_name)`) rather than generic shell executors.
- Every parameter must be strictly validated against allowlists or regex patterns using Pydantic.
- Tools must be categorized by risk tier (`READ_ONLY` vs `MUTATING`), where mutating actions require cryptographically verified human approval before execution.

