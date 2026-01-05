from __future__ import annotations

from typing import Any, Dict


def hello(input: Dict[str, Any] | None = None, *, name: str | None = None) -> Dict[str, Any]:
    """Example tool.

    Supports either:
    - hello({"name": "Vishwa"})
    - hello(name="Vishwa")
    """
    if input and isinstance(input, dict) and name is None:
        name = input.get("name")
    who = (name or "world").strip() or "world"
    return {"message": f"Hello, {who}!"}
