import pytest
from pydantic import ValidationError
from app.graph.state import IncidentDiagnosis
from app.rag.structured_parser import StructuredOutputParser, StructuredParsingError


def test_clean_json_parsing():
    """Verify clean JSON directly validates into IncidentDiagnosis model."""
    raw = '''{
        "incident_id": "INC-4091",
        "service_name": "orders-db",
        "severity": "SEV1",
        "suspected_root_cause": "Database connection saturation due to lock wait timeouts",
        "impacted_components": ["checkout-api", "payment-service"],
        "confidence_score": 0.95
    }'''
    result = StructuredOutputParser.parse(raw, IncidentDiagnosis)
    assert result.incident_id == "INC-4091"
    assert result.severity == "SEV1"
    assert result.confidence_score == 0.95
    assert len(result.impacted_components) == 2


def test_markdown_fence_and_preamble_stripping():
    """Verify parser extracts JSON from conversational greetings and markdown code blocks."""
    raw = '''Sure! Here is the structured diagnosis you requested:

```json
{
    "incident_id": "INC-8821",
    "service_name": "auth-redis",
    "severity": "SEV2",
    "suspected_root_cause": "Eviction policy OOM error under burst traffic",
    "impacted_components": ["auth-gateway"],
    "confidence_score": 0.88
}
```

Let me know if you need any follow-up diagnostics!'''

    result = StructuredOutputParser.parse(raw, IncidentDiagnosis)
    assert result.incident_id == "INC-8821"
    assert result.service_name == "auth-redis"
    assert result.severity == "SEV2"


def test_invalid_severity_literal_rejected():
    """Verify that hallucinated severity strings like 'CRITICAL' are rejected."""
    raw = '''{
        "incident_id": "INC-1002",
        "service_name": "billing-api",
        "severity": "CRITICAL",
        "suspected_root_cause": "Payment processor network socket timeout",
        "impacted_components": ["billing-web"],
        "confidence_score": 0.90
    }'''
    with pytest.raises(ValidationError) as exc_info:
        StructuredOutputParser.parse(raw, IncidentDiagnosis)
    
    errors = str(exc_info.value)
    assert "severity" in errors
    assert "Input should be 'SEV1', 'SEV2', 'SEV3' or 'SEV4'" in errors


def test_custom_incident_id_prefix_validator():
    """Verify that IDs missing 'INC-' prefix fail custom @field_validator."""
    raw = '''{
        "incident_id": "ALERT-9999",
        "service_name": "billing-api",
        "severity": "SEV3",
        "suspected_root_cause": "Intermittent packet loss on eth0 interface",
        "impacted_components": ["internal-metrics"],
        "confidence_score": 0.75
    }'''
    with pytest.raises(ValidationError) as exc_info:
        StructuredOutputParser.parse(raw, IncidentDiagnosis)
    
    assert "Incident ID must start with 'INC-'" in str(exc_info.value)


def test_self_healing_reflection_loop_recovers():
    """Verify that a malformed output is repaired using the simulated LLM reflection loop."""
    bad_initial_output = '''{
        "incident_id": "BAD-123",
        "service_name": "payment-ingress",
        "severity": "URGENT",
        "suspected_root_cause": "OOMKilled container exit code 137",
        "impacted_components": ["checkout"],
        "confidence_score": 0.80
    }'''

    def mock_llm_repair(prompt: str) -> str:
        assert "VALIDATION ERRORS" in prompt
        assert "TARGET JSON SCHEMA" in prompt
        return '''{
            "incident_id": "INC-1234",
            "service_name": "payment-ingress",
            "severity": "SEV1",
            "suspected_root_cause": "OOMKilled container exit code 137",
            "impacted_components": ["checkout"],
            "confidence_score": 0.80
        }'''

    diagnosis, history = StructuredOutputParser.parse_with_repair(
        bad_initial_output,
        IncidentDiagnosis,
        repair_llm_fn=mock_llm_repair,
        max_retries=2
    )

    assert diagnosis.incident_id == "INC-1234"
    assert diagnosis.severity == "SEV1"
    assert len(history) == 1


def test_max_retries_exceeded_raises_error():
    """Verify that if LLM persistently returns invalid JSON, StructuredParsingError is raised."""
    bad_output = '{"broken_json": true'

    def stubborn_mock_llm(prompt: str) -> str:
        return '{"still_broken": true'

    with pytest.raises(StructuredParsingError):
        StructuredOutputParser.parse_with_repair(
            bad_output,
            IncidentDiagnosis,
            repair_llm_fn=stubborn_mock_llm,
            max_retries=2
        )
