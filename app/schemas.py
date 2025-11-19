from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EntryCategory(str, Enum):
    NOTE = "note"
    PROGRESS = "progress"


class EntryBase(BaseModel):
    project: Optional[str] = Field(
        default=None,
        description="Logical project name this entry belongs to",
    )
    category: EntryCategory = Field(
        default=EntryCategory.NOTE,
        description="Type of entry: generic note or structured project progress",
    )
    content_raw: str = Field(..., description="Original text as submitted by the user")
    tags: List[str] = Field(
        default_factory=list,
        description="Free-form tags, e.g. ['backend', 'milestone-1']",
    )

    # Progress logging convention
    progress_stage: Optional[str] = Field(
        default=None,
        description="For progress entries: stage or phase name, e.g. 'design', 'implementation', 'review'",
    )
    progress_notes: Optional[str] = Field(
        default=None,
        description="Optional structured progress note separate from the main content",
    )


class EntryCreate(EntryBase):
    pass


class EntryNormalized(EntryBase):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the entry was accepted by the service",
    )
    source: str = Field(
        default="unknown",
        description="Origin of the entry, e.g. 'web_form' or 'api'",
    )
    content_normalized: str = Field(
        ...,
        description="Normalized text after applying service-level cleanup rules",
    )


def normalize_content(text: str) -> str:
    """
    Apply simple, stable normalization to free-text content.

    This is intentionally minimal and deterministic:
      - strip leading/trailing whitespace
      - collapse runs of blank lines
      - normalize line endings to '\n'
    """
    if not text:
        return ""

    # Normalize line endings and strip outer whitespace
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    # Collapse multiple blank lines
    lines = normalized.split("\n")
    collapsed: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = line.strip() == ""
        if is_blank and previous_blank:
            continue
        collapsed.append(line.rstrip())
        previous_blank = is_blank

    return "\n".join(collapsed)


def build_normalized_entry(
    payload: EntryCreate,
    *,
    source: str,
) -> EntryNormalized:
    return EntryNormalized(
        **payload.model_dump(),
        source=source,
        content_normalized=normalize_content(payload.content_raw),
    )


class ValueTag(str, Enum):
    HUMAN_TOUCH = "HumanTouch"
    DIFFERENTIATION = "Differentiation"
    EFFICIENCY = "Efficiency"
    INTEGRITY = "Integrity"
    GROWTH = "Growth"
    BRAND_TRUST = "BrandTrust"


class ArtifactType(str, Enum):
    PROPOSAL = "Proposal"
    DEMO = "Demo"
    DESIGN = "Design"
    TRUST_ARTIFACT = "TrustArtifact"
    WORKFLOW_DECISION = "WorkflowDecision"
    NOTE = "Note"


class LedgerEntryBase(BaseModel):
    title: str = Field(..., description="Short descriptor for quick scanning")
    summary: str = Field(..., description="Narrative summary / key outcomes")
    theme: str = Field(..., description="High-level theme, e.g. Workflow, AI_PM")
    lens: str = Field(..., description="Perspective/agent lens, e.g. CuriosityArchitect")
    project: Optional[str] = Field(default=None, description="Project or initiative name")
    value_tags: List[ValueTag] = Field(default_factory=list)
    artifact_tags: List[ArtifactType] = Field(default_factory=list)
    references: List[str] = Field(
        default_factory=list,
        description="Optional references (SharePoint links, PRs, prompts, etc.)",
    )


class LedgerEntryCreate(LedgerEntryBase):
    pass


class LedgerEntryNormalized(LedgerEntryBase):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    month_tag: str = Field(..., description="Derived #Month/YYYY-MM tag")
    tags: List[str] = Field(default_factory=list, description="Expanded tag list with prefixes")
    actor: Optional[str] = Field(default=None, description="Person/service recording the entry")
    source: str = Field(default="unknown", description="Origin channel")


def build_ledger_entry(
    payload: LedgerEntryCreate,
    *,
    source: str,
    actor: Optional[str] = None,
) -> LedgerEntryNormalized:
    created = datetime.now(timezone.utc)
    month_tag = created.strftime("%Y-%m")
    tags = [
        f"#Theme/{payload.theme}",
        f"#Lens/{payload.lens}",
        f"#Month/{month_tag}",
    ]
    tags.extend(f"#{tag.value}" for tag in payload.value_tags)
    tags.extend(f"#{tag.value}" for tag in payload.artifact_tags)

    return LedgerEntryNormalized(
        **payload.model_dump(),
        id=str(uuid4()),
        created_at=created,
        month_tag=month_tag,
        tags=tags,
        actor=actor,
        source=source,
    )


class TodoStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TodoEntryBase(BaseModel):
    title: str = Field(..., description="Short task summary")
    details: Optional[str] = Field(default=None, description="Long-form notes")
    status: TodoStatus = Field(default=TodoStatus.PENDING)
    due_date: Optional[str] = Field(
        default=None,
        description="Optional due date string (flexible format for now)",
    )
    tags: List[str] = Field(default_factory=list, description="Free-form tags")


class TodoEntryCreate(TodoEntryBase):
    pass


class TodoEntryNormalized(TodoEntryBase):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    month_tag: str = Field(..., description="YYYY-MM bucket")


def build_todo_entry(payload: TodoEntryCreate) -> TodoEntryNormalized:
    created = datetime.now(timezone.utc)
    return TodoEntryNormalized(
        **payload.model_dump(),
        month_tag=created.strftime("%Y-%m"),
        created_at=created,
    )
