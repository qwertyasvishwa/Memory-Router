from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_SAFE_ID_RE = re.compile(r"[^a-z0-9-_]")


def _sanitize_id(value: str) -> str:
    value = (value or "").strip().lower()
    value = _SAFE_ID_RE.sub("", value)
    return value


def _samples_root() -> Path:
    # <repo>/app/static/tools/brand-guidelines/samples
    return Path(__file__).resolve().parent / "static" / "tools" / "brand-guidelines" / "samples"


@dataclass(frozen=True)
class BrandGuidelinesSample:
    id: str
    name: str
    description: str
    data: dict[str, Any]


def list_brand_guidelines_samples() -> list[BrandGuidelinesSample]:
    root = _samples_root()
    if not root.exists():
        return []

    out: list[BrandGuidelinesSample] = []
    for sample_json in sorted(root.glob("*/sample.json")):
        try:
            data = json.loads(sample_json.read_text(encoding="utf-8"))
        except Exception:
            continue

        folder_id = sample_json.parent.name
        sample_id = _sanitize_id(str(data.get("id") or folder_id))
        if not sample_id:
            continue

        name = str(data.get("name") or sample_id).strip() or sample_id
        description = str(data.get("description") or "").strip()
        out.append(BrandGuidelinesSample(id=sample_id, name=name, description=description, data=data))

    out.sort(key=lambda s: s.name.lower())
    return out


def load_brand_guidelines_sample(sample_id: str) -> dict[str, Any]:
    safe = _sanitize_id(sample_id)
    if not safe:
        raise FileNotFoundError("Invalid sample id")

    path = _samples_root() / safe / "sample.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    data_id = _sanitize_id(str(data.get("id") or safe))
    if data_id != safe:
        data["id"] = safe

    data["name"] = str(data.get("name") or safe).strip() or safe
    data["description"] = str(data.get("description") or "").strip()
    return data


def resolve_static_paths(sample: dict[str, Any]) -> dict[str, Any]:
    """
    Adds `exists` flags for any image assets listed under:
      sample["assets"]["images"] = [{ "src": "/static/..." , ... }]
    """
    images = (((sample or {}).get("assets") or {}).get("images") or [])
    if not isinstance(images, list):
        return sample

    static_root = Path(__file__).resolve().parent / "static"
    for img in images:
        if not isinstance(img, dict):
            continue
        src = str(img.get("src") or "").strip()
        if not src.startswith("/static/"):
            img["exists"] = False
            continue
        rel = src[len("/static/") :]
        img["exists"] = (static_root / rel).exists()

    return sample

