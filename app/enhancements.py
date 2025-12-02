import csv
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EnhancementLogCreate(BaseModel):
    title: str = Field(..., description="Short description of the enhancement or change")
    description: str = Field(..., description="Narrative describing what was built or changed")
    reason: str = Field(..., description="Why the change was required (root driver)")
    area: str = Field(..., description="Layer or capability touched, e.g., API, UI, infra")
    impact: str = Field(..., description="Intended impact such as UX clarity, performance, compliance")
    tags: List[str] = Field(default_factory=list, description="Free-form tags")
    links: List[str] = Field(default_factory=list, description="References to PRs, tickets, docs")


class EnhancementLogEntry(EnhancementLogCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    month_tag: str = Field(..., description="YYYY-MM bucket for filtering")


class ImprovementSuggestion(BaseModel):
    title: str
    rationale: str
    next_steps: List[str]


class EnhancementLogService:
    LOG_COLUMNS = [
        "timestamp",
        "id",
        "title",
        "description",
        "reason",
        "area",
        "impact",
        "tags",
        "links",
    ]

    KEYWORD_SUGGESTIONS: Dict[str, Dict[str, str]] = {
        "performance": {
            "title": "Extend performance profiling",
            "next": "Instrument critical endpoints to quantify the next bottleneck.",
        },
        "latency": {
            "title": "Tighten latency budgets",
            "next": "Add synthetic monitoring to catch latency regressions early.",
        },
        "ux": {
            "title": "Deepen UX consistency",
            "next": "Schedule a UI audit to harmonize patterns across routes.",
        },
        "ui": {
            "title": "Deepen UX consistency",
            "next": "Schedule a UI audit to harmonize patterns across routes.",
        },
        "observability": {
            "title": "Expand observability signals",
            "next": "Add tracing/log enrichment so future changes surface context automatically.",
        },
        "automation": {
            "title": "Broaden automation coverage",
            "next": "Look for manual flows adjacent to recent automation wins.",
        },
        "security": {
            "title": "Refresh security posture",
            "next": "Run a lightweight threat-model review around the touched area.",
        },
        "documentation": {
            "title": "Boost knowledge capture",
            "next": "Add runbooks or inline docs to keep information fresh.",
        },
    }

    def __init__(self, log_path: Optional[str | Path] = None) -> None:
        self.log_path = Path(log_path or "enhancements_log.csv").resolve()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._ensure_log_file()
        self._entries: List[EnhancementLogEntry] = self._load_entries()

    def _ensure_log_file(self) -> None:
        if self.log_path.exists():
            return
        with self.log_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(self.LOG_COLUMNS)

    def _load_entries(self) -> List[EnhancementLogEntry]:
        if not self.log_path.exists():
            return []
        entries: List[EnhancementLogEntry] = []
        with self.log_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                entry = self._row_to_entry(row)
                if entry:
                    entries.append(entry)
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries

    def _row_to_entry(self, row: Dict[str, str]) -> Optional[EnhancementLogEntry]:
        try:
            created = datetime.fromisoformat(row["timestamp"])
            tags = json.loads(row.get("tags") or "[]")
            links = json.loads(row.get("links") or "[]")
            return EnhancementLogEntry(
                id=row["id"],
                created_at=created,
                month_tag=created.strftime("%Y-%m"),
                title=row["title"],
                description=row["description"],
                reason=row["reason"],
                area=row["area"],
                impact=row["impact"],
                tags=tags,
                links=links,
            )
        except (KeyError, ValueError, json.JSONDecodeError):
            return None

    def record_entry(self, payload: EnhancementLogCreate) -> EnhancementLogEntry:
        with self._lock:
            entry = EnhancementLogEntry(
                **payload.model_dump(),
                month_tag=datetime.now(timezone.utc).strftime("%Y-%m"),
            )
            with self.log_path.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        entry.created_at.isoformat(),
                        entry.id,
                        entry.title,
                        entry.description,
                        entry.reason,
                        entry.area,
                        entry.impact,
                        json.dumps(entry.tags, ensure_ascii=False),
                        json.dumps(entry.links, ensure_ascii=False),
                    ]
                )
            self._entries.insert(0, entry)
            logger.info("Enhancement logged title=%s area=%s", entry.title, entry.area)
            return entry

    def list_entries(self, limit: Optional[int] = None) -> List[EnhancementLogEntry]:
        with self._lock:
            entries = list(self._entries)
        return entries[:limit] if limit else entries

    def generate_suggestions(self, limit: int = 5) -> List[ImprovementSuggestion]:
        entries = self.list_entries()
        if not entries:
            return [
                ImprovementSuggestion(
                    title="Capture first enhancement",
                    rationale="No enhancement history detected. Start logging wins to unlock tailored recommendations.",
                    next_steps=[
                        "Document the latest change (UI, API, automation) with reasoning and impact.",
                        "Revisit this view to unlock proactive suggestions.",
                    ],
                )
            ]

        suggestions: List[ImprovementSuggestion] = []
        area_counter = Counter(entry.area for entry in entries)
        tag_counter = Counter(tag.lower() for entry in entries for tag in entry.tags)
        keyword_hits = defaultdict(int)
        for entry in entries:
            lowered_reason = entry.reason.lower()
            for keyword in self.KEYWORD_SUGGESTIONS:
                if keyword in lowered_reason:
                    keyword_hits[keyword] += 1

        most_recent = entries[0]
        suggestions.append(
            ImprovementSuggestion(
                title=f"Follow-up on “{most_recent.title}”",
                rationale=(
                    f"The latest enhancement targeted {most_recent.area} to achieve {most_recent.impact}. "
                    "Validate outcomes and line up the adjacent improvement."
                ),
                next_steps=[
                    "Review telemetry/feedback confirming the impact.",
                    f"Identify the next dependency in {most_recent.area} that still matches the reason: {most_recent.reason}.",
                ],
            )
        )

        least_attended_area = min(area_counter.items(), key=lambda item: item[1])
        suggestions.append(
            ImprovementSuggestion(
                title=f"Rebalance focus on {least_attended_area[0]}",
                rationale=(
                    f"{least_attended_area[0]} has only {least_attended_area[1]} logged enhancements, "
                    "indicating a potential gap compared to other areas."
                ),
                next_steps=[
                    f"Audit {least_attended_area[0]} for UX/quality issues.",
                    f"Log a roadmap item to raise the baseline for {least_attended_area[0]}.",
                ],
            )
        )

        if tag_counter:
            top_tag, freq = tag_counter.most_common(1)[0]
            suggestions.append(
                ImprovementSuggestion(
                    title=f"Double-down on #{top_tag}",
                    rationale=f"Tag #{top_tag} appears in {freq} enhancements, proving high leverage.",
                    next_steps=[
                        f"Explore adjacent features that benefit from the #{top_tag} theme.",
                        "Document learnings so other contributors can replicate the win.",
                    ],
                )
            )

        for keyword, count in sorted(keyword_hits.items(), key=lambda item: item[1], reverse=True):
            suggestion_meta = self.KEYWORD_SUGGESTIONS[keyword]
            suggestions.append(
                ImprovementSuggestion(
                    title=suggestion_meta["title"],
                    rationale=f"Multiple enhancements cited {keyword}, so keep momentum on that driver.",
                    next_steps=[suggestion_meta["next"]],
                )
            )
            if len(suggestions) >= limit:
                break

        return suggestions[:limit]


enhancement_log_service = EnhancementLogService()


def build_enhancement_report(entries: List[EnhancementLogEntry]) -> str:
    lines: List[str] = [
        "# Enhancement Log Export",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Total enhancements: {len(entries)}",
        "",
    ]
    for entry in reversed(entries):
        lines.append(f"## {entry.title} ({entry.created_at.strftime('%Y-%m-%d %H:%M UTC')})")
        lines.append(f"- **Area:** {entry.area}")
        lines.append(f"- **Impact:** {entry.impact}")
        lines.append(f"- **Reason:** {entry.reason}")
        if entry.tags:
            lines.append(f"- **Tags:** {', '.join(entry.tags)}")
        if entry.links:
            lines.append("- **References:**")
            for link in entry.links:
                lines.append(f"  - {link}")
        lines.append("")
        lines.append(entry.description)
        lines.append("")
    return "\n".join(lines)
