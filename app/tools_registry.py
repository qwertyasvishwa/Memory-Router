from __future__ import annotations

import importlib
import inspect
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolSpec(BaseModel):
    """Declarative tool definition.

    This is intentionally simple so you can support:
    - end-user tools (run from UI)
    - developer tools (scaffold/run in repo)

    The actual implementation can be:
    - kind="builtin" with an entrypoint (python callable)
    - kind="prompt" (future: LLM-backed, not implemented in MVP)
    """

    id: str = Field(..., description="Unique tool id")
    name: str = Field(..., description="Human-friendly name")
    description: str = Field(default="")
    kind: str = Field(default="builtin", description="builtin | prompt | external")

    # For builtin tools: module:function path, e.g. "app.tools.sample:hello"
    entrypoint: Optional[str] = Field(default=None)

    # Simple JSON-schema-like hints (not enforced in MVP)
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)


class ToolCreate(BaseModel):
    id: str
    name: str
    description: str = ""
    kind: str = "builtin"
    entrypoint: Optional[str] = None
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)


class ToolRunRequest(BaseModel):
    input: Dict[str, Any] = Field(default_factory=dict)


class ToolRunResult(BaseModel):
    ok: bool
    tool_id: str
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class _ResolvedEntrypoint:
    module: str
    attr: str
    fn: Callable[..., Any]


def _parse_entrypoint(entrypoint: str) -> tuple[str, str]:
    if ":" not in entrypoint:
        raise ValueError("Entrypoint must look like 'module:path', e.g. 'app.tools.sample:hello'")
    mod, attr = entrypoint.split(":", 1)
    mod, attr = mod.strip(), attr.strip()
    if not mod or not attr:
        raise ValueError("Entrypoint must include both module and attribute")
    return mod, attr


def _resolve_entrypoint(entrypoint: str) -> _ResolvedEntrypoint:
    module_name, attr = _parse_entrypoint(entrypoint)
    module = importlib.import_module(module_name)
    fn = getattr(module, attr, None)
    if fn is None:
        raise ValueError(f"Entrypoint attribute not found: {module_name}:{attr}")
    if not callable(fn):
        raise ValueError(f"Entrypoint is not callable: {module_name}:{attr}")
    return _ResolvedEntrypoint(module=module_name, attr=attr, fn=fn)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def list_tools(self) -> List[ToolSpec]:
        return sorted(self._tools.values(), key=lambda t: t.id)

    def get(self, tool_id: str) -> ToolSpec:
        if tool_id not in self._tools:
            raise KeyError(tool_id)
        return self._tools[tool_id]

    def upsert(self, payload: ToolCreate) -> ToolSpec:
        spec = ToolSpec(**payload.model_dump())
        self._tools[spec.id] = spec
        return spec

    def delete(self, tool_id: str) -> None:
        if tool_id in self._tools:
            del self._tools[tool_id]

    def run(self, tool_id: str, request: ToolRunRequest) -> ToolRunResult:
        try:
            spec = self.get(tool_id)
        except KeyError:
            return ToolRunResult(ok=False, tool_id=tool_id, error="Tool not found")

        if spec.kind != "builtin":
            return ToolRunResult(
                ok=False,
                tool_id=tool_id,
                error="Only kind='builtin' tools are supported in MVP",
            )
        if not spec.entrypoint:
            return ToolRunResult(ok=False, tool_id=tool_id, error="Missing entrypoint")

        try:
            resolved = _resolve_entrypoint(spec.entrypoint)
            fn = resolved.fn

            # Convention: function accepts a single dict argument named input, or **kwargs.
            sig = inspect.signature(fn)
            if len(sig.parameters) == 1:
                output = fn(request.input)
            else:
                output = fn(**request.input)

            if output is None:
                output_dict: Dict[str, Any] = {}
            elif isinstance(output, dict):
                output_dict = output
            else:
                output_dict = {"result": output}

            return ToolRunResult(ok=True, tool_id=tool_id, output=output_dict)
        except Exception as exc:
            logger.exception("Tool run failed tool=%s", tool_id)
            return ToolRunResult(ok=False, tool_id=tool_id, error=str(exc))


tool_registry = ToolRegistry()

# Seed one example tool so the UI/API has something immediately usable.
# You can remove this once you start adding tools through the API.
try:
    tool_registry.upsert(
        ToolCreate(
            id="hello",
            name="Hello tool",
            description="Tiny built-in example tool",
            kind="builtin",
            entrypoint="app.tools_sample:hello",
            input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        )
    )
except Exception:
    pass
