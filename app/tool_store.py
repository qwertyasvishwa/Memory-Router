from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from .tools_registry import ToolCreate, ToolSpec, tool_registry

logger = logging.getLogger(__name__)


def default_tools_path() -> Path:
    # repo_root/.memory_router/tools.json
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / ".memory_router" / "tools.json"


def load_tools(path: Path | None = None) -> List[ToolSpec]:
    p = path or default_tools_path()
    if not p.exists():
        return []

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        tools = data.get("tools", []) if isinstance(data, dict) else []
        loaded: List[ToolSpec] = []
        for t in tools:
            spec = ToolSpec.model_validate(t)
            tool_registry.upsert(ToolCreate(**spec.model_dump()))
            loaded.append(spec)
        logger.info("Loaded %d tools from %s", len(loaded), p)
        return loaded
    except Exception as exc:
        logger.warning("Failed to load tools from %s: %s", p, exc)
        return []


def save_tools(path: Path | None = None) -> None:
    p = path or default_tools_path()
    p.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": 1,
        "tools": [t.model_dump(mode="json") for t in tool_registry.list_tools()],
    }
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Saved %d tools to %s", len(data["tools"]), p)
