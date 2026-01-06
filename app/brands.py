from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BrandSpec:
    id: str
    name: str
    logo_url: str | None = None


def _brands_dir() -> Path:
    return Path(__file__).resolve().parent / "static" / "brands"


def list_brands() -> list[BrandSpec]:
    """
    Discover brands from `app/static/brands/<brand>/brand.json`.

    This keeps the "brand list" data-driven, so generators/tools can work across
    multiple brands without code changes.
    """
    base = _brands_dir()
    if not base.exists():
        return []

    brands: list[BrandSpec] = []
    for brand_dir in sorted([p for p in base.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        spec_path = brand_dir / "brand.json"
        if not spec_path.exists():
            continue
        try:
            raw = json.loads(spec_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        brand_id = str(raw.get("id") or brand_dir.name).strip()
        if not brand_id:
            continue
        name = str(raw.get("name") or brand_id).strip()
        logo_url = raw.get("logoUrl")
        if logo_url is not None and not isinstance(logo_url, str):
            logo_url = None

        brands.append(BrandSpec(id=brand_id, name=name, logo_url=logo_url))

    brands.sort(key=lambda b: (b.name.lower(), b.id.lower()))
    return brands


def load_brand_config(brand_id: str) -> dict[str, Any] | None:
    base = _brands_dir() / brand_id / "brand.json"
    if not base.exists():
        return None
    try:
        return json.loads(base.read_text(encoding="utf-8"))
    except Exception:
        return None

