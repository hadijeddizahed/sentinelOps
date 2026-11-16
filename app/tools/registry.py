import time
from typing import Any, Callable, Dict, List, Literal, Optional, Type  # noqa: UP035

from pydantic import BaseModel, Field, ValidationError

ToolScope = Literal["READ_ONLY", "MUTATING"]
ToolStatus = Literal["SUCCESS", "ERROR", "PERMISSION_DENIED"]


class ToolResult(BaseModel):
    """Standardized result returned by any tool execution."""

    tool_name: str
    status: ToolStatus
    data: Optional[Any] = None
    error: Optional[str] = None
    scope: ToolScope
    execution_time_ms: float = Field(default=0.0)
    observation: str = Field(description="Formatted text observation for LLM context")


class ToolDefinition:
    """Internal metadata descriptor for a registered tool."""

    def __init__(
        self,
        name: str,
        description: str,
        args_schema: Type[BaseModel],
        func: Callable[..., Any],
        scope: ToolScope = "READ_ONLY",
    ):
        self.name = name
        self.description = description
        self.args_schema = args_schema
        self.func = func
        self.scope = scope

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert tool schema to standard OpenAI / Anthropic function declaration format."""
        schema = self.args_schema.model_json_schema()
        # Clean up internal pydantic metadata
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }


class ToolRegistry:
    """Central registry and execution dispatcher for agent tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self, name: Optional[str] = None, scope: ToolScope = "READ_ONLY"
    ) -> Callable:
        """Decorator to register a function with its typed Pydantic argument schema."""

        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            docstring = (func.__doc__ or "No description provided.").strip()

            # Inspect function annotations to locate the Pydantic schema argument
            annotations = getattr(func, "__annotations__", {})
            schema_type = None
            for param_name, param_type in annotations.items():
                if (
                    param_name != "return"
                    and isinstance(param_type, type)
                    and issubclass(param_type, BaseModel)
                ):
                    schema_type = param_type
                    break

            if schema_type is None:
                raise ValueError(
                    f"Tool function '{tool_name}' must accept a Pydantic model as an argument."
                )

            tool_def = ToolDefinition(
                name=tool_name,
                description=docstring,
                args_schema=schema_type,
                func=func,
                scope=scope,
            )
            self._tools[tool_name] = tool_def
            return func

        return decorator

    def list_tools(self) -> List[ToolDefinition]:
        """Return all registered tool definitions."""
        return list(self._tools.values())

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return all tool declarations formatted for LLM function calling."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def execute(
        self, tool_name: str, arguments: Dict[str, Any], allow_mutations: bool = False
    ) -> ToolResult:
        """Execute a tool with argument validation and safety scope checks.

        Exceptions are caught and packaged into the ToolResult observation
        to enable agent self-correction.
        """
        start_time = time.perf_counter()

        # 1. Existence check
        if tool_name not in self._tools:
            elapsed = (time.perf_counter() - start_time) * 1000
            err_msg = f"Tool '{tool_name}' not found. Available tools: {list(self._tools.keys())}"
            return ToolResult(
                tool_name=tool_name,
                status="ERROR",
                error=err_msg,
                scope="READ_ONLY",
                execution_time_ms=elapsed,
                observation=f"Observation: [Tool Execution Failed] {err_msg}",
            )

        tool = self._tools[tool_name]

        # 2. Safety Scope Authorization Guard
        if tool.scope == "MUTATING" and not allow_mutations:
            elapsed = (time.perf_counter() - start_time) * 1000
            err_msg = f"Action '{tool_name}' is categorized as MUTATING and requires explicit human approval."
            return ToolResult(
                tool_name=tool_name,
                status="PERMISSION_DENIED",
                error=err_msg,
                scope=tool.scope,
                execution_time_ms=elapsed,
                observation=f"Observation: [Permission Denied] {err_msg}",
            )

        # 3. Pydantic Argument Validation
        try:
            validated_args = tool.args_schema.model_validate(arguments)
        except ValidationError as val_err:
            elapsed = (time.perf_counter() - start_time) * 1000
            errors_str = "; ".join(
                f"{'->'.join(str(l) for l in e['loc'])}: {e['msg']}"
                for e in val_err.errors()
            )
            err_msg = f"Invalid arguments for tool '{tool_name}': {errors_str}"
            return ToolResult(
                tool_name=tool_name,
                status="ERROR",
                error=err_msg,
                scope=tool.scope,
                execution_time_ms=elapsed,
                observation=f"Observation: [Schema Validation Error] {err_msg}. Please adjust your parameters and retry.",
            )

        # 4. Safe Execution Dispatching
        try:
            raw_output = tool.func(validated_args)
            elapsed = (time.perf_counter() - start_time) * 1000
            obs_str = (
                f"Observation from {tool_name}:\n{raw_output}"
                if isinstance(raw_output, str)
                else f"Observation from {tool_name}:\n{raw_output}"
            )
            return ToolResult(
                tool_name=tool_name,
                status="SUCCESS",
                data=raw_output,
                scope=tool.scope,
                execution_time_ms=elapsed,
                observation=obs_str,
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start_time) * 1000
            err_msg = f"Runtime error executing '{tool_name}': {str(exc)}"
            return ToolResult(
                tool_name=tool_name,
                status="ERROR",
                error=err_msg,
                scope=tool.scope,
                execution_time_ms=elapsed,
                observation=f"Observation: [API Runtime Error] {err_msg}. Consider checking resource state or alternative tools.",
            )
