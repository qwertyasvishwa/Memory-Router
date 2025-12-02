import csv
import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, List, Optional, Set, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field, validator

try:  # Optional dependency for .msg files
    import extract_msg  # type: ignore
except Exception:  # pragma: no cover - best-effort import
    extract_msg = None

logger = logging.getLogger(__name__)


class ActivityType(str, Enum):
    CAMPAIGN_EXECUTION = "campaign_execution"
    PRODUCT_DESIGN = "product_design"
    ENGINEERING_DELIVERY = "engineering_delivery"
    TRAINING_ENABLEMENT = "training_enablement"
    OPS_COMPLIANCE = "ops_compliance"
    PERFORMANCE_REPORTING = "performance_reporting"

    @property
    def display_name(self) -> str:
        return self.value.replace("_", " ").title()

    @property
    def icon(self) -> str:
        icons = {
            "campaign_execution": "📣",
            "product_design": "🎨",
            "engineering_delivery": "⚙️",
            "training_enablement": "🎓",
            "ops_compliance": "🛡️",
            "performance_reporting": "📊"
        }
        return icons.get(self.value, "📋")


class WeeklyTaskSubmission(BaseModel):
    project: Optional[str] = Field(
        default=None,
        description="Optional project or initiative name related to this update.",
    )
    context: Optional[str] = Field(
        default=None,
        description="Optional context or source label for the update (weekly sync, e-mail, etc.).",
    )
    activity_type: ActivityType = Field(
        default=ActivityType.CAMPAIGN_EXECUTION,
        description="Categorizes the task for filtering/reporting.",
    )
    update: str = Field(..., description="Raw communication that should produce macro tasks.")

    @validator("update")
    def update_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Update content must not be empty")
        return value


def _strip_subject_prefix(subject: str) -> str:
    lowered = subject.lstrip()
    for prefix in ("re:", "fw:", "fwd:"):
        if lowered.lower().startswith(prefix):
            return lowered[len(prefix) :].lstrip()
    return subject.strip()


def _strip_html(text: str) -> str:
    # Very lightweight HTML tag stripping for email bodies.
    return re.sub(r"<[^>]+>", "", text)


def _parse_eml(content: bytes) -> Tuple[Optional[str], Optional[str], str]:
    message = BytesParser(policy=policy.default).parsebytes(content)
    subject = _strip_subject_prefix(message.get("subject") or "")
    sender = (message.get("from") or "").strip()
    recipients = (message.get("to") or "").strip()
    date = (message.get("date") or "").strip()

    body_text = ""
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                body_text = part.get_content()
                break
        if not body_text:
            for part in message.walk():
                if part.get_content_type() == "text/html":
                    body_text = _strip_html(part.get_content())
                    break
    else:
        if message.get_content_type().startswith("text/"):
            body_text = message.get_content()

    body_text = (body_text or "").strip()
    context_parts = []
    if sender:
        context_parts.append(f"From {sender}")
    if recipients:
        context_parts.append(f"to {recipients}")
    if date:
        context_parts.append(f"on {date}")
    context = ", ".join(context_parts)
    if subject:
        if context:
            context = f"{context}: {subject}"
        else:
            context = subject

    project = subject or None
    update_text = body_text or context or subject or ""
    return project or None, context or None, update_text


def _parse_msg(content: bytes) -> Tuple[Optional[str], Optional[str], str]:
    if extract_msg is None:
        raise ValueError("MSG parsing requires the extract-msg package to be installed")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".msg") as temp:
        temp.write(content)
        temp_path = temp.name

    try:
        message = extract_msg.Message(temp_path)  # type: ignore[attr-defined]
        subject = _strip_subject_prefix(message.subject or "")
        sender = (message.sender or "").strip()
        recipients = (message.to or "").strip()
        date = (str(message.date) or "").strip()
        body_text = (message.body or "").strip()
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    context_parts = []
    if sender:
        context_parts.append(f"From {sender}")
    if recipients:
        context_parts.append(f"to {recipients}")
    if date:
        context_parts.append(f"on {date}")
    context = ", ".join(context_parts)
    if subject:
        if context:
            context = f"{context}: {subject}"
        else:
            context = subject

    project = subject or None
    update_text = body_text or context or subject or ""
    return project or None, context or None, update_text


def parse_outlook_email(filename: str, content: bytes) -> Tuple[Optional[str], Optional[str], str]:
    """
    Parse an Outlook email file (.eml or .msg) and return
    (project, context, update_text) for the weekly tracker.
    """
    name = filename.lower()
    if name.endswith(".eml"):
        return _parse_eml(content)
    if name.endswith(".msg"):
        return _parse_msg(content)
    raise ValueError("Unsupported email file type; expected .eml or .msg")


class WeeklyTaskSummary(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    project: Optional[str]
    context: Optional[str]
    activity_type: ActivityType
    input_excerpt: str
    generated_tasks: List[str]
    overlooked_tasks: List[str]


class WeeklyTaskTracker:
    LOG_COLUMNS = [
        "timestamp",
        "id",
        "project",
        "context",
        "activity_type",
        "input_excerpt",
        "generated_tasks",
        "overlooked_tasks",
    ]

    SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
    OVERLOOK_KEYWORDS = [
        "should",
        "need",
        "must",
        "pending",
        "blocked",
        "waiting",
        "awaiting",
        "unresolved",
        "delayed",
        "follow-up",
        "tie-back",
        "risk",
    ]

    def __init__(self, log_path: Optional[str | Path] = None) -> None:
        self.log_path = Path(log_path or "weekly_tasks_log.csv").resolve()
        self._lock = Lock()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_log_file()
        self._upgrade_log_file()
        self._tasks_seen: Set[str] = self._load_seen_tasks()

    def _ensure_log_file(self) -> None:
        if self.log_path.exists():
            return
        with self.log_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(self.LOG_COLUMNS)

    def _load_seen_tasks(self) -> Set[str]:
        seen: Set[str] = set()
        if not self.log_path.exists():
            return seen
        with self.log_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                timestamp = row.get("timestamp")
                if not timestamp:
                    continue
                try:
                    created = datetime.fromisoformat(timestamp)
                except ValueError:
                    continue
                window = self._window_slug(created, row.get("project") or None)
                for column in ("generated_tasks", "overlooked_tasks"):
                    raw = row.get(column) or "[]"
                    try:
                        tasks = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    for task in tasks:
                        seen.add(self._seen_key(window, task))
        return seen

    def _upgrade_log_file(self) -> None:
        if not self.log_path.exists():
            return
        with self.log_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fieldnames = reader.fieldnames
        if fieldnames == self.LOG_COLUMNS:
            return
        with self.log_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.LOG_COLUMNS)
            writer.writeheader()
            for row in rows:
                row = row or {}
                if "activity_type" not in row or not row["activity_type"]:
                    row["activity_type"] = ActivityType.CAMPAIGN_EXECUTION.value
                writer.writerow({column: row.get(column, "") for column in self.LOG_COLUMNS})

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.split()).lower()

    def _split_sentences(self, text: str) -> List[str]:
        segments = [segment.strip() for segment in self.SENTENCE_SPLIT_RE.split(text) if segment.strip()]
        return segments

    def _shape_macro_task(self, sentence: str) -> str:
        sentence = sentence.strip().rstrip(".!?")
        if not sentence:
            return ""
        first_word = sentence.split()[0]
        sentence_cased = sentence[0].upper() + sentence[1:]
        if first_word.lower() in {"lead", "drive", "coordinate", "own", "ensure", "deliver", "ship", "validate", "plan", "oversee", "accelerate"}:
            return f"{sentence_cased}."

        return f"Drive {sentence_cased}."

    def _generate_macro_tasks(self, sentences: Iterable[str]) -> List[str]:
        tasks: List[str] = []
        for sentence in sentences:
            if len(sentence.split()) <= 3:
                continue
            task_text = self._shape_macro_task(sentence)
            if task_text:
                tasks.append(task_text)
        return tasks

    def _generate_overlooked_tasks(self, sentences: Iterable[str], project: Optional[str]) -> List[str]:
        overrides: List[str] = []
        for sentence in sentences:
            lowered = sentence.lower()
            if any(keyword in lowered for keyword in self.OVERLOOK_KEYWORDS):
                cleaned = re.sub(r"\b(should|shouldn't|need|needs|must|mustn't|pending|blocked|waiting|awaiting|unresolved|delayed|risk|follow-up|follow up)\b", "", sentence, flags=re.IGNORECASE)
                cleaned = cleaned.strip().rstrip(".!?")
                if not cleaned:
                    continue
                overrides.append(f"Ensure follow-up on {cleaned}.")
        if not overrides:
            base_target = project or "this initiative"
            overrides.append(f"Confirm metrics, risks, and stakeholder alignment for {base_target} before the next sync.")
        return overrides

    def _record_new_task(self, task: str, *, window: str) -> bool:
        normalized = self._seen_key(window, task)
        if normalized in self._tasks_seen:
            return False
        self._tasks_seen.add(normalized)
        return True

    def _window_slug(self, created: datetime, project: Optional[str]) -> str:
        iso = created.isocalendar()
        project_key = (project or "general").strip().lower() or "general"
        return f"{iso.year}-W{iso.week:02d}:{project_key}"

    def _seen_key(self, window: str, task: str) -> str:
        return f"{window}|{self._normalize(task)}"

    def _append_log(self, summary: WeeklyTaskSummary) -> None:
        with self.log_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    summary.created_at.isoformat(),
                    summary.id,
                    summary.project or "",
                    summary.context or "",
                    summary.activity_type.value,
                    summary.input_excerpt,
                    json.dumps(summary.generated_tasks, ensure_ascii=False),
                    json.dumps(summary.overlooked_tasks, ensure_ascii=False),
                ]
            )

    def process_update(self, submission: WeeklyTaskSubmission) -> WeeklyTaskSummary:
        with self._lock:
            text = submission.update.strip()
            created_at = datetime.now(timezone.utc)
            window = self._window_slug(created_at, submission.project)
            sentences = self._split_sentences(text)
            generated_candidates = self._generate_macro_tasks(sentences)
            generated: List[str] = []
            for candidate in generated_candidates:
                if self._record_new_task(candidate, window=window):
                    generated.append(candidate)

            overlooked_candidates = self._generate_overlooked_tasks(sentences, submission.project)
            overlooked: List[str] = []
            for candidate in overlooked_candidates:
                if self._record_new_task(candidate, window=window):
                    overlooked.append(candidate)

            if not generated:
                generated = [
                    "No new macro-level tasks detected beyond the items already tracked in the weekly tracker."
                ]
            if not overlooked:
                fallback = (
                    f"Reconfirm risks and dependencies for {submission.project or 'the initiative'} "
                    "if they change in future updates."
                )
                overlooked.append(fallback)

            excerpt = text[:240]

            summary = WeeklyTaskSummary(
                project=submission.project,
                context=submission.context,
                activity_type=submission.activity_type,
                input_excerpt=excerpt,
                generated_tasks=generated,
                overlooked_tasks=overlooked,
                created_at=created_at,
            )
            self._append_log(summary)
            logger.info(
                "Weekly task report recorded project=%s entries=%d overlooked=%d",
                submission.project,
                len(generated),
                len(overlooked),
            )
        return summary

    def history(self, limit: int = 20) -> List[WeeklyTaskSummary]:
        with self._lock:
            if not self.log_path.exists():
                return []
            rows: List[WeeklyTaskSummary] = []
            with self.log_path.open("r", newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    summary = self._row_to_summary(row)
                    if summary:
                        rows.append(summary)
            rows.sort(key=lambda entry: entry.created_at, reverse=True)
            return rows[:limit]

    def get_summary(self, summary_id: str) -> Optional[WeeklyTaskSummary]:
        with self._lock:
            if not self.log_path.exists():
                return None
            with self.log_path.open("r", newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    if row.get("id") == summary_id:
                        return self._row_to_summary(row)
        return None

    def _row_to_summary(self, row: dict[str, str]) -> Optional[WeeklyTaskSummary]:
        try:
            created = datetime.fromisoformat(row["timestamp"])
            generated = json.loads(row.get("generated_tasks") or "[]")
            overlooked = json.loads(row.get("overlooked_tasks") or "[]")
            raw_activity = row.get("activity_type")
            try:
                activity = ActivityType(raw_activity) if raw_activity else ActivityType.CAMPAIGN_EXECUTION
            except ValueError:
                activity = ActivityType.CAMPAIGN_EXECUTION
            return WeeklyTaskSummary(
                id=row["id"],
                created_at=created,
                project=row.get("project") or None,
                context=row.get("context") or None,
                activity_type=activity,
                input_excerpt=row.get("input_excerpt", ""),
                generated_tasks=generated,
                overlooked_tasks=overlooked,
            )
        except (KeyError, ValueError, json.JSONDecodeError):
            return None


def build_weekly_report(entries: List[WeeklyTaskSummary]) -> str:
    lines: List[str] = [
        "# Weekly Task Tracker Export",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Total entries: {len(entries)}",
        "",
    ]
    for entry in reversed(entries):
        header = entry.project or "General update"
        lines.append(f"## {header} ({entry.created_at.strftime('%Y-%m-%d %H:%M UTC')})")
        lines.append(f"*Activity type:* {entry.activity_type.value.replace('_', ' ').title()}")
        if entry.context:
            lines.append(f"**Context:** {entry.context}")
        lines.append("")
        lines.append("### Macro tasks")
        for task in entry.generated_tasks:
            lines.append(f"- {task}")
        lines.append("")
        lines.append("### Overlooked / missing tasks")
        for task in entry.overlooked_tasks:
            lines.append(f"- {task}")
        lines.append("")
    return "\n".join(lines)


def filter_entries(
    entries: List[WeeklyTaskSummary],
    *,
    project: Optional[str] = None,
    activity_type: Optional[str] = None,
    activity_types: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    keyword: Optional[str] = None,
) -> List[WeeklyTaskSummary]:
    from datetime import datetime

    filtered = entries

    # Project filter
    if project:
        term = project.lower()
        filtered = [entry for entry in filtered if entry.project and term in entry.project.lower()]

    # Activity type filter (single or multiple)
    if activity_type:
        try:
            target = ActivityType(activity_type)
            filtered = [entry for entry in filtered if entry.activity_type == target]
        except ValueError:
            pass
    elif activity_types:
        valid_types = []
        for at in activity_types:
            try:
                valid_types.append(ActivityType(at))
            except ValueError:
                pass
        if valid_types:
            filtered = [entry for entry in filtered if entry.activity_type in valid_types]

    # Date range filter
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            filtered = [entry for entry in filtered if entry.created_at >= from_date]
        except ValueError:
            pass

    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            filtered = [entry for entry in filtered if entry.created_at <= to_date]
        except ValueError:
            pass

    # Keyword search
    if keyword:
        term = keyword.lower()
        filtered = [entry for entry in filtered if (
            (entry.context and term in entry.context.lower()) or
            (entry.project and term in entry.project.lower()) or
            (entry.input_excerpt and term in entry.input_excerpt.lower()) or
            any(term in task.lower() for task in entry.generated_tasks) or
            any(term in task.lower() for task in entry.overlooked_tasks)
        )]

    return filtered


def get_project_summary(entries: List[WeeklyTaskSummary]) -> Dict[str, Dict[str, int]]:
    """Generate project-wise activity summary"""
    from collections import defaultdict
    summary: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for entry in entries:
        project = entry.project or "Uncategorized"
        activity = entry.activity_type.value
        summary[project][activity] += 1
        summary[project]['total'] += 1

    return dict(summary)


def get_activity_summary(entries: List[WeeklyTaskSummary]) -> Dict[str, int]:
    """Generate activity type summary"""
    from collections import Counter
    counter = Counter(entry.activity_type.value for entry in entries)
    return dict(counter)