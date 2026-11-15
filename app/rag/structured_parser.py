import json
import re
from typing import Type, TypeVar, Optional, Callable, Tuple, List, Any
from pydantic import BaseModel, ValidationError


T = TypeVar("T", bound=BaseModel)

class StructuredParsingError(Exception):
    """Raised when parsing fails and cannot be recovered within the retry budget."""
    pass

class StructuredOutputParser:
    """Robust parser for LLM-generated JSON with automated validation reflection."""
    @staticmethod
    def extract_json_payload(raw_text: str) -> str:
        """Strip markdown fences, conversational preambles, and extract raw JSON object or array."""
        cleaned = raw_text.strip()

        # 1. Match code fence ```json ... ``` or ``` ... ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if fence_match:
            cleaned = fence_match.group(1).strip()

        # 2. Find outer-most braces { ... } or brackets [ ... ] if surrounding text exists
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")

        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            cleaned = cleaned[first_brace: last_brace + 1]

        return cleaned

    @classmethod
    def parse(cls, raw_text: str, schema: Type[T])->T:
        """Parse and validate raw text directly against a Pydantic schema."""
        cleaned_json = cls.extract_json_payload(raw_text)
        try:
            return schema.model_validate_json(cleaned_json)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise exc

    @classmethod
    def format_validation_errors(cls, error: ValidationError) -> List[str]:
        """Convert Pydantic validation error objects into readable instructions for an LLM."""
        formatted = []
        for err in error.errors():
            loc = " -> ".join(str(p) for p in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            input_val = err.get("input", "<omitted>")
            formatted.append(f"Field '{loc}': {msg} (received input: {input_val!r})")
        return formatted

    @classmethod
    def build_repair_prompt(
            cls,
            raw_text: str,
            schema: Type[T],
            error_details: List[str]
    ) -> str:
        """Generate a focused reflection prompt instructing the LLM to fix its schema violations."""
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        errors_text = "\n".join(f"- {e}" for e in error_details)
        return (
            "Your previous response failed strict schema validation.\n\n"
            f"=== VALIDATION ERRORS ===\n{errors_text}\n\n"
            f"=== TARGET JSON SCHEMA ===\n{schema_json}\n\n"
            f"=== YOUR PREVIOUS OUTPUT ===\n{raw_text}\n\n"
            "INSTRUCTION: Output ONLY the corrected, valid JSON object satisfying the schema above. "
            "Do NOT include any conversational text, explanations, or markdown code fences."
        )

    @classmethod
    def parse_with_repair(
            cls,
            raw_text: str,
            schema: Type[T],
            repair_llm_fn: Optional[Callable[[str], str]] = None,
            max_retries: int = 2
    ) -> Tuple[T, List[str]]:
        """Parse with automated self-healing retry loop.

        Returns:
            Tuple of (ValidatedModel, List of repair prompt history)
        """
        current_text = raw_text
        repair_history: List[str] = []
        for attempt in range(max_retries + 1):
            try:
                result = cls.parse(current_text, schema)
                return result, repair_history
            except (ValidationError, json.JSONDecodeError) as exc:
                if attempt == max_retries or repair_llm_fn is None:
                    raise StructuredParsingError(
                        f"Failed to parse into {schema.__name__} after {attempt} retries: {exc}"
                    ) from exc
                # Format error for reflection
                if isinstance(exc, ValidationError):
                    error_details = cls.format_validation_errors(exc)
                else:
                    error_details = [f"JSON syntax error: {exc}"]
                repair_prompt = cls.build_repair_prompt(current_text, schema, error_details)
                repair_history.append(repair_prompt)

                # Request corrected output from LLM
                current_text = repair_llm_fn(repair_prompt)
        raise StructuredParsingError(f"Exceeded max retries ({max_retries}) for schema {schema.__name__}")





