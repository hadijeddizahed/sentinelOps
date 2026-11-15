# Day 02: Advanced Prompting & Structured Outputs

**Phase:** Week 1 — Advanced LLM Engineering & Knowledge Intelligence  
**Focus:** Constrained JSON Generation, Pydantic Schema Enforcement, Grammar Sampling, and Self-Healing Validation Loops

---

## 1. Executive Summary & Why This Matters

Autonomous systems cannot parse conversational prose like *"I think the database is experiencing connection issues, please try restarting PgBouncer"*. Production operations demand strict, type-safe data contracts (`RemediationAction(action="RESTART", service="pgbouncer", timeout=30)`). If an LLM outputs malformed JSON, hallucinates an invalid enum literal, or omits required fields, the entire remediation pipeline crashes.

Today, you will master structured output generation: moving from basic prompt hints to bulletproof data contracts using **Pydantic v2**, JSON Schema enforcement, grammar-constrained decoding principles, and exponential-backoff **self-healing reflection loops**.

---

## 2. Learning Objectives

By the end of today, you will understand and be able to:
1. **Design strict schemas in Pydantic v2:** Use field constraints (`gt`, `lt`, `min_length`, regex patterns, `Literal` types, and custom `@field_validator` functions).
2. **Compare the 3 Paradigms of Structured Outputs:**
   - **Prompt-Only ("Please output JSON"):** Stochastic, fragile, prone to markdown ticks and extra text.
   - **Model-Native JSON Mode & Function Calling:** Provider-level constrained decoding.
   - **Grammar-Constrained Decoding (CFG / FSM):** Logit masking at sampling time guaranteeing 100% syntactic conformity.
3. **Build a Self-Healing Validation Loop:** Catch Pydantic `ValidationError` exceptions, extract the exact JSON schema path that failed, feed the error back into the LLM context, and have the model self-correct.
4. **Prepare SentinelOps State Ingestion:** Turn messy raw cloud alerts into strongly typed `IncidentDiagnosis` models.

---

## 3. Technical Deep-Dive

### A. The Three Paradigms of Structured Extraction

```
1. Prompt-Only Extraction:
   "Output valid JSON matching this schema: {...}"
   ❌ Weakness: Model outputs ```json ... ```, preambles ("Here is your JSON:"), trailing commas.

2. Model-Native Structured Output (OpenAI / Anthropic):
   Forces output tokens to adhere to a strict JSON Schema definition.
   ⚠️ Limitation: API-dependent, requires modern hosted models.

3. Grammar-Constrained Decoding (Outlines, Guidance, llama.cpp grammars):
   Builds a Finite State Machine (FSM) from the JSON schema regex/grammar.
   During sampling, tokens violating the grammar receive a logit mask of -inf.
   ✅ Strength: Mathematically impossible for the model to produce invalid syntax.
```

### B. The Self-Healing Validation Cycle

When an LLM produces output that violates business logic (e.g. `severity="URGENT"` instead of `Literal["SEV1", "SEV2", "SEV3"]`):

```
[ Raw LLM Output ] ───► [ Pydantic v2 Validator ]
                                │
                 ┌──────────────┴──────────────┐
                 ▼ (Pass)                      ▼ (ValidationError)
        [ Validated State ]             [ Error Inspector ]
                                               │
                                               ▼
                                  [ Self-Healing Prompt ]
                                  "Your output failed validation:
                                   Field 'severity' must be SEV1, SEV2, or SEV3.
                                   Please output corrected JSON only."
                                               │
                                               ▼
                                      [ Retry LLM Call ]
```

---

## 4. Curated Learning Resources

### High-Impact YouTube Lectures
1. **Jason Liu — "Driving LLMs to Strict Outputs with Pydantic & Instructor"**
   - **URL:** https://www.youtube.com/watch?v=yj-wSRJwrrc
   - **Channel:** Jason Liu / AI Engineering
   - *Why watch:* The definitive industry talk on modeling complex real-world data schemas with Pydantic and handling validation retries.
2. **Hamel Husain — "Creating Structured Data with LLMs & Reliable Extraction"**
   - **URL:** https://www.youtube.com/watch?v=vVwP_nQyL0w
   - **Channel:** Hamel Husain
   - *Why watch:* Pragmatic engineering advice on why prompt-based JSON fails in production and how to test structured LLM pipelines.
3. **Lance Martin (LangChain) — "Structured Outputs and Tool Calling in LangChain"**
   - **URL:** https://www.youtube.com/watch?v=0k3F_QvPqE8
   - **Channel:** LangChain
   - *Why watch:* Walks through `with_structured_output`, Pydantic integration, and schema validation.

### Official Documentation
- **Pydantic v2 JSON Schema Guide:** https://docs.pydantic.dev/latest/concepts/json_schema/
- **OpenAI Structured Outputs Guide:** https://platform.openai.com/docs/guides/structured-outputs
- **Outlines (Grammar-Constrained Generation):** https://dottxt-ai.github.io/outlines/

---

## 5. Hands-on Guided Exercise (Conceptual Prototype)

Here is how a self-healing parser works in pure Python:

```python
from pydantic import BaseModel, Field, ValidationError
from typing import Literal, List
import json

class IncidentDiagnosis(BaseModel):
    service_name: str = Field(description="Name of the affected service")
    severity: Literal["SEV1", "SEV2", "SEV3"] = Field(description="Normalized severity level")
    impacted_endpoints: List[str] = Field(min_length=1, description="List of API routes affected")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence between 0.0 and 1.0")

def parse_and_repair(raw_llm_json: str) -> IncidentDiagnosis:
    try:
        data = json.loads(raw_llm_json)
        return IncidentDiagnosis.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as err:
        print(f"Validation failed with error: {err}")
        print("Constructing self-healing repair prompt...")
        # In step-by-step coding, we feed this exact error message back into the model
        repaired_json = '''{
            "service_name": "orders-db",
            "severity": "SEV1",
            "impacted_endpoints": ["/api/v1/orders", "/api/v1/checkout"],
            "confidence_score": 0.95
        }'''
        return IncidentDiagnosis.model_validate_json(repaired_json)

if __name__ == "__main__":
    # Test with invalid severity 'CRITICAL' instead of 'SEV1'|'SEV2'|'SEV3'
    bad_payload = '{"service_name": "orders-db", "severity": "CRITICAL", "impacted_endpoints": []}'
    result = parse_and_repair(bad_payload)
    print("Repaired result:", result.model_dump())
```

---

## 6. SentinelOps Core Implementation Plan (What We Will Code)

When we begin the coding phase, we will implement this step-by-step:
1. **Step 1:** Define the strict SRE data models in `app/graph/state.py` (e.g. `IncidentDiagnosis`, `TriageAlert`, `RemediationProposal`).
2. **Step 2:** Build `app/rag/structured_parser.py` with the `StructuredIncidentParser` class that implements:
   - Schema generation from Pydantic.
   - JSON extraction (stripping markdown fences).
   - Automated reflection prompt formatting on validation failure.
3. **Step 3:** Write comprehensive unit tests in `tests/unit/test_structured_parser.py` verifying that invalid enums, empty arrays, and malformed JSON are cleanly handled.

---

## 7. Exit Criteria Checklist

- [ ] Studied the differences between Prompt-only JSON, Native Structured Outputs, and Grammar Masking.
- [ ] Understand how Pydantic v2 `ValidationError` gives the exact JSON path of invalid fields.
- [ ] Ready to code the SentinelOps structured parser step-by-step.

---

## 8. Senior AI Engineer Interview Prep

**Q1: Why is asking an LLM for JSON via prompt engineering unreliable in high-throughput production, and what are the failure modes?**  
*Model Answer:*  
Language models predict tokens probabilistically based on training distributions. In prompt-only JSON:
1. **Extraneous Tokens:** Models often wrap output in markdown codeblocks (` ```json `), add conversational greetings ("Sure, here is the JSON:"), or add trailing comments.
2. **Schema Drift:** As prompt context gets longer, attention dispersion can lead the model to drop required keys, hallucinate extra keys, or change casing (e.g., `incidentId` instead of `incident_id`).
3. **Syntactic Corruption:** Under high temperature or long generation sequences, models frequently produce unescaped quotes inside string values or trailing commas, causing standard JSON parsers (`json.loads`) to throw fatal exceptions.

**Q2: How does Grammar-Constrained Decoding (like Outlines / llama.cpp CFG grammars) guarantee 100% valid JSON?**  
*Model Answer:*  
Grammar-constrained decoding operates directly on the model's vocabulary logit vector at every sampling step. The Pydantic JSON schema is converted into a deterministic Regular Expression or Context-Free Grammar (CFG) represented as a Finite State Machine (FSM). Before sampling the next token, the FSM determines which tokens in the vocabulary are syntactically valid transitions. All invalid token logits are masked to $-\infty$. Thus, the model is mathematically prohibited from selecting a token that would violate the schema syntax.

