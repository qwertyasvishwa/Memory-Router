import io
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, Form, HTTPException, Query, Request, UploadFile, File, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from .enhancements import (
    EnhancementLogCreate,
    EnhancementLogEntry,
    EnhancementLogService,
    ImprovementSuggestion,
    build_enhancement_report,
)
from .config import get_settings
from .ledger import ledger_service
from .schemas import (
    ArtifactType,
    EntryCategory,
    EntryCreate,
    EntryNormalized,
    LedgerEntryCreate,
    LedgerEntryNormalized,
    TodoEntryCreate,
    TodoEntryNormalized,
    ValueTag,
    build_ledger_entry,
    build_normalized_entry,
)
from .sharepoint_client import graph_client
from .todos import todo_service
from .weekly_tasks import (
    ActivityType,
    WeeklyTaskSubmission,
    WeeklyTaskTracker,
    WeeklyTaskSummary,
    build_weekly_report,
    filter_entries,
    parse_outlook_email,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("memory_router")

QUICK_LINKS = [
    {
        "label": "Memory Router folder",
        "url": "https://vishwaraj04.sharepoint.com/sites/Vishwa/Shared%20Documents/Memory%20Router",
    },
    {
        "label": "Drive (Vishwa)",
        "url": "https://vishwaraj04.sharepoint.com/sites/Vishwa/Shared%20Documents",
    },
]

def _parse_enum_list(raw: Optional[str], enum_cls):
    values: List = []
    if not raw:
        return values
    for part in raw.split(","):
        cleaned = part.strip().lstrip("#").split("/")[-1]
        if not cleaned:
            continue
        for enum_member in enum_cls:
            if cleaned.lower() == enum_member.value.lower():
                values.append(enum_member)
                break
    return values


async def _record_ledger_for_entry(
    entry: EntryNormalized,
    *,
    item_id: str,
    source: str,
) -> None:
    summary = entry.content_normalized[:240] or entry.content_raw[:240]
    artifact_tag = ArtifactType.NOTE if entry.category == EntryCategory.NOTE else ArtifactType.WORKFLOW_DECISION
    try:
        await ledger_service.log_entry(
            LedgerEntryCreate(
                title=f"{entry.category.value.title()} entry captured",
                summary=summary,
                theme="Workflow",
                lens="MemoryRouter",
                project=entry.project,
                value_tags=[ValueTag.GROWTH, ValueTag.EFFICIENCY],
                artifact_tags=[artifact_tag],
                references=[
                    f"https://graph.microsoft.com/v1.0/drives/{graph_client.settings.drive_id}/items/{item_id}"
                ],
            ),
            source=source,
            actor="memory-router",
        )
    except Exception as exc:
        logger.warning("Failed to log ledger entry for %s: %s", entry.id, exc)

app = FastAPI(title="Memory Router", version="0.1.0")

templates = Jinja2Templates(directory="app/templates")

# In-memory session view of accepted entries (not a database).
IN_MEMORY_ENTRIES: List[EntryNormalized] = []
_settings = get_settings()
weekly_tracker = WeeklyTaskTracker(log_path=_settings.weekly_log_path)
enhancement_log_service = EnhancementLogService(log_path=_settings.enhancement_log_path)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    todos = todo_service.list_entries()
    ledger_entries = ledger_service.list_entries()[:5]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "quick_links": QUICK_LINKS,
            "todos": todos,
            "recent_ledger": ledger_entries,
        },
    )


@app.get("/drive", response_class=HTMLResponse)
async def browse_drive(
    request: Request,
    path: Optional[str] = None,
    drive_id: Optional[str] = None,
) -> HTMLResponse:
    """
    Simple browser over drives accessible to the app registration.
    """
    selected_drive_id = drive_id or graph_client.settings.drive_id
    use_default_drive = selected_drive_id == graph_client.settings.drive_id and drive_id is None
    base_folder = None if use_default_drive else ""

    logger.info(
        "Drive browse requested drive=%s path=%s", selected_drive_id, path or "/"
    )
    try:
        items = await graph_client.list_children(
            path,
            drive_id=selected_drive_id,
            base_folder=base_folder,
        )
        drives = await graph_client.list_available_drives()
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to list drive items: {exc}",
        ) from exc

    # Normalize path for display / navigation
    normalized_path = (path or "").strip("/")
    segments = [seg for seg in normalized_path.split("/") if seg] if normalized_path else []

    return templates.TemplateResponse(
        "drive.html",
        {
            "request": request,
            "items": items,
            "path": normalized_path,
            "segments": segments,
            "selected_drive_id": selected_drive_id,
            "drives": drives,
        },
    )


@app.get("/ledger", response_class=HTMLResponse)
async def ledger_view(request: Request) -> HTMLResponse:
    entries = ledger_service.list_entries()
    return templates.TemplateResponse(
        "ledger.html",
        {
            "request": request,
            "entries": entries,
            "value_tags": list(ValueTag),
            "artifact_tags": list(ArtifactType),
        },
    )


@app.post("/todos", response_class=HTMLResponse)
async def create_todo(
    request: Request,
    title: str = Form(...),
    details: Optional[str] = Form(default=None),
    due_date: Optional[str] = Form(default=None),
    tags: Optional[str] = Form(default=None),
) -> HTMLResponse:
    payload = TodoEntryCreate(
        title=title,
        details=details or None,
        due_date=due_date or None,
        tags=[t.strip() for t in (tags or "").split(",") if t.strip()],
    )
    try:
        await todo_service.add_entry(payload)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to record todo: {exc}",
        ) from exc
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/weekly-tasks", response_class=HTMLResponse)
async def weekly_tasks_view(
    request: Request,
    highlight: Optional[str] = None,
    project: Optional[str] = None,
    activity_type: Optional[str] = None,
    activity_types: Optional[List[str]] = Query(default=None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    keyword: Optional[str] = None,
    group_by: Optional[str] = None,
) -> HTMLResponse:
    from .weekly_tasks import get_project_summary, get_activity_summary

    history = weekly_tracker.history(limit=200)

    filtered_history = filter_entries(
        history,
        project=project,
        activity_type=activity_type,
        activity_types=activity_types,
        date_from=date_from,
        date_to=date_to,
        keyword=keyword
    )

    # Get all unique projects for dropdown
    all_projects = sorted(list(set([entry.project for entry in history if entry.project])))

    # Generate summaries
    project_summary = get_project_summary(filtered_history)
    activity_summary = get_activity_summary(filtered_history)

    summary = None
    if highlight:
        summary = next((entry for entry in history if entry.id == highlight), None)
        if summary is None:
            summary = weekly_tracker.get_summary(highlight)
    if not summary:
        summary = filtered_history[0] if filtered_history else (history[0] if history else None)
    highlight_id = highlight or (summary.id if summary else None)
    export_status = request.query_params.get("export")
    export_item_id = request.query_params.get("item_id")

    return templates.TemplateResponse(
        "weekly_tasks.html",
        {
            "request": request,
            "weekly_summary": summary,
            "weekly_history": filtered_history,
            "highlight_id": highlight_id,
            "export_status": export_status,
            "export_item_id": export_item_id,
            "project_filter": project or "",
            "activity_filter": activity_type or "",
            "activity_types_filter": activity_types or [],
            "date_from_filter": date_from or "",
            "date_to_filter": date_to or "",
            "keyword_filter": keyword or "",
            "group_by": group_by or "",
            "activity_types": list(ActivityType),
            "all_projects": all_projects,
            "project_summary": project_summary,
            "activity_summary": activity_summary,
            "total_entries": len(filtered_history),
        },
    )


@app.post("/weekly-tasks", response_class=HTMLResponse)
async def weekly_tasks_submit(
    project: Optional[str] = Form(default=None),
    context: Optional[str] = Form(default=None),
    update: Optional[str] = Form(default=None),
    activity_type: ActivityType = Form(default=ActivityType.CAMPAIGN_EXECUTION),
    email_file: Optional[UploadFile] = File(default=None),
) -> HTMLResponse:
    submission: WeeklyTaskSubmission
    if email_file and email_file.filename:
        contents = await email_file.read()
        try:
            parsed_project, parsed_context, parsed_update = parse_outlook_email(email_file.filename, contents)
            submission = WeeklyTaskSubmission(
                project=project or parsed_project,
                context=context or parsed_context,
                activity_type=activity_type,
                update=parsed_update,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse email file: {exc}",
            ) from exc
    else:
        if not update:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Update text is required when no email file is provided.",
            )
        submission = WeeklyTaskSubmission(
            project=project or None,
            context=context or None,
            activity_type=activity_type,
            update=update,
        )
    summary = weekly_tracker.process_update(submission)
    return RedirectResponse(
        url=f"/weekly-tasks?highlight={summary.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/weekly-tasks/export", response_class=HTMLResponse)
async def weekly_tasks_export() -> HTMLResponse:
    history = weekly_tracker.history(limit=500)
    if not history:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No weekly tracker entries to export.")
    report = build_weekly_report(history)
    filename = f"weekly-tasks-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.md"
    try:
        item_id = await graph_client.upload_text_document(
            report,
            filename=filename,
            subfolder="reports/weekly-tracker",
            content_type="text/markdown",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload weekly tracker export: {exc}",
        ) from exc

    return RedirectResponse(
        url=f"/weekly-tasks?export=ok&item_id={item_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get("/weekly-tasks/list", response_class=HTMLResponse)
async def weekly_tasks_list(
    request: Request,
    project: Optional[str] = None,
    activity_type: Optional[str] = None,
    activity_types: Optional[List[str]] = Query(default=None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    keyword: Optional[str] = None,
    group_by: Optional[str] = None,
) -> HTMLResponse:
    from .weekly_tasks import get_project_summary, get_activity_summary

    history = weekly_tracker.history(limit=500)

    filtered_history = filter_entries(
        history,
        project=project,
        activity_type=activity_type,
        activity_types=activity_types,
        date_from=date_from,
        date_to=date_to,
        keyword=keyword
    )

    # Get all unique projects for dropdown
    all_projects = sorted(list(set([entry.project for entry in history if entry.project])))

    # Generate summaries
    project_summary = get_project_summary(filtered_history)
    activity_summary = get_activity_summary(filtered_history)

    return templates.TemplateResponse(
        "weekly_tasks_list.html",
        {
            "request": request,
            "weekly_history": filtered_history,
            "project_filter": project or "",
            "activity_filter": activity_type or "",
            "activity_types_filter": activity_types or [],
            "date_from_filter": date_from or "",
            "date_to_filter": date_to or "",
            "keyword_filter": keyword or "",
            "group_by": group_by or "",
            "activity_types": list(ActivityType),
            "all_projects": all_projects,
            "project_summary": project_summary,
            "activity_summary": activity_summary,
            "total_entries": len(filtered_history),
        },
    )


@app.get("/enhancements", response_class=HTMLResponse)
async def enhancements_view(request: Request) -> HTMLResponse:
    entries = enhancement_log_service.list_entries(limit=50)
    suggestions = enhancement_log_service.generate_suggestions(limit=5)
    export_status = request.query_params.get("export")
    export_item_id = request.query_params.get("item_id")
    return templates.TemplateResponse(
        "enhancements.html",
        {
            "request": request,
            "entries": entries,
            "suggestions": suggestions,
            "export_status": export_status,
            "export_item_id": export_item_id,
        },
    )


@app.post("/enhancements", response_class=HTMLResponse)
async def enhancements_submit(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    reason: str = Form(...),
    area: str = Form(...),
    impact: str = Form(...),
    tags: Optional[str] = Form(default=None),
    links: Optional[str] = Form(default=None),
) -> HTMLResponse:
    payload = EnhancementLogCreate(
        title=title,
        description=description,
        reason=reason,
        area=area,
        impact=impact,
        tags=[t.strip() for t in (tags or "").split(",") if t.strip()],
        links=[line.strip() for line in (links or "").splitlines() if line.strip()],
    )
    enhancement_log_service.record_entry(payload)
    return RedirectResponse(url="/enhancements", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/enhancements/export", response_class=HTMLResponse)
async def enhancements_export() -> HTMLResponse:
    entries = enhancement_log_service.list_entries()
    if not entries:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No enhancements to export.")
    report = build_enhancement_report(entries)
    filename = f"enhancements-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.md"
    try:
        item_id = await graph_client.upload_text_document(
            report,
            filename=filename,
            subfolder="reports/enhancements",
            content_type="text/markdown",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload enhancement report: {exc}",
        ) from exc
    return RedirectResponse(
        url=f"/enhancements?export=ok&item_id={item_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/ledger", response_class=HTMLResponse)
async def ledger_form_submit(
    request: Request,
    title: str = Form(...),
    summary: str = Form(...),
    theme: str = Form(...),
    lens: str = Form(...),
    project: Optional[str] = Form(default=None),
    value_tags: Optional[str] = Form(default=None),
    artifact_tags: Optional[str] = Form(default=None),
    references: Optional[str] = Form(default=None),
) -> HTMLResponse:
    payload = LedgerEntryCreate(
        title=title,
        summary=summary,
        theme=theme,
        lens=lens,
        project=project or None,
        value_tags=_parse_enum_list(value_tags, ValueTag),
        artifact_tags=_parse_enum_list(artifact_tags, ArtifactType),
        references=[line.strip() for line in (references or "").splitlines() if line.strip()],
    )
    try:
        await ledger_service.log_entry(payload, source="web-ledger", actor="memory-router")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to record ledger entry: {exc}",
        ) from exc

    return RedirectResponse(url="/ledger", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/api/drive/children")
async def api_drive_children(path: Optional[str] = None, drive_id: Optional[str] = None) -> JSONResponse:
    """
    JSON API for listing items in a drive (defaults to configured drive).
    """
    selected_drive_id = drive_id or graph_client.settings.drive_id
    use_default_drive = selected_drive_id == graph_client.settings.drive_id and drive_id is None
    base_folder = None if use_default_drive else ""

    logger.info(
        "API drive listing drive=%s path=%s", selected_drive_id, path or "/"
    )
    try:
        items = await graph_client.list_children(
            path,
            drive_id=selected_drive_id,
            base_folder=base_folder,
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to list drive items: {exc}",
        ) from exc

    return JSONResponse(content={"path": path or "", "drive_id": selected_drive_id, "items": items})


@app.get("/api/drives")
async def api_list_drives() -> JSONResponse:
    logger.info("API drive list requested")
    try:
        drives = await graph_client.list_available_drives()
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to list drives: {exc}",
        ) from exc
    return JSONResponse(content={"drives": drives})


@app.get("/drive/download/{item_id}")
async def download_drive_item(item_id: str, drive_id: Optional[str] = None) -> StreamingResponse:
    logger.info("Download requested item=%s drive=%s", item_id, drive_id or "default")
    try:
        content, content_type, filename = await graph_client.download_item(
            item_id,
            drive_id=drive_id,
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to download file: {exc}",
        ) from exc

    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.post("/api/ledger", response_model=LedgerEntryNormalized)
async def api_log_ledger(payload: LedgerEntryCreate) -> LedgerEntryNormalized:
    try:
        entry = await ledger_service.log_entry(payload, source="api-ledger", actor="api")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to record ledger entry: {exc}",
        ) from exc
    return entry


@app.get("/api/ledger", response_model=List[LedgerEntryNormalized])
async def api_list_ledger_entries() -> List[LedgerEntryNormalized]:
    return ledger_service.list_entries()


@app.post("/api/todos", response_model=TodoEntryNormalized)
async def api_create_todo(payload: TodoEntryCreate) -> TodoEntryNormalized:
    try:
        return await todo_service.add_entry(payload)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to record todo: {exc}",
        ) from exc


@app.get("/api/todos", response_model=List[TodoEntryNormalized])
async def api_list_todos() -> List[TodoEntryNormalized]:
    return todo_service.list_entries()


@app.post("/api/weekly-tasks", response_model=WeeklyTaskSummary)
async def api_weekly_tasks(payload: WeeklyTaskSubmission) -> WeeklyTaskSummary:
    return weekly_tracker.process_update(payload)


@app.get("/api/weekly-tasks/history", response_model=List[WeeklyTaskSummary])
async def api_weekly_history(limit: Optional[int] = 20) -> List[WeeklyTaskSummary]:
    return weekly_tracker.history(limit=limit or 20)


@app.post("/api/enhancements", response_model=EnhancementLogEntry)
async def api_create_enhancement(payload: EnhancementLogCreate) -> EnhancementLogEntry:
    return enhancement_log_service.record_entry(payload)


@app.get("/api/enhancements", response_model=List[EnhancementLogEntry])
async def api_list_enhancements(limit: Optional[int] = None) -> List[EnhancementLogEntry]:
    return enhancement_log_service.list_entries(limit=limit)


@app.get("/api/enhancements/suggestions", response_model=List[ImprovementSuggestion])
async def api_enhancement_suggestions(limit: Optional[int] = 5) -> List[ImprovementSuggestion]:
    return enhancement_log_service.generate_suggestions(limit=limit or 5)


@app.get("/enhancements/report", response_class=HTMLResponse)
async def enhancement_report(request: Request) -> HTMLResponse:
    entries = enhancement_log_service.list_entries()
    return templates.TemplateResponse(
        "enhancements_report.html",
        {
            "request": request,
            "entries": entries,
        },
    )


@app.get("/entries", response_class=HTMLResponse)
async def list_entries_view(request: Request) -> HTMLResponse:
    # Newest first
    entries = sorted(IN_MEMORY_ENTRIES, key=lambda e: e.created_at, reverse=True)
    return templates.TemplateResponse(
        "entries.html",
        {
            "request": request,
            "entries": entries,
        },
    )


@app.get("/api/entries", response_model=List[EntryNormalized])
async def list_entries_api() -> List[EntryNormalized]:
    return sorted(IN_MEMORY_ENTRIES, key=lambda e: e.created_at, reverse=True)


@app.post("/submit", response_class=HTMLResponse)
async def submit_form(
    request: Request,
    content: str = Form(...),
    project: Optional[str] = Form(default=None),
    category: EntryCategory = Form(default=EntryCategory.NOTE),
    tags: Optional[str] = Form(default=None),
    progress_stage: Optional[str] = Form(default=None),
    progress_notes: Optional[str] = Form(default=None),
) -> HTMLResponse:
    tags_list: List[str] = []
    if tags:
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]

    payload = EntryCreate(
        project=project or None,
        category=category,
        content_raw=content,
        tags=tags_list,
        progress_stage=progress_stage or None,
        progress_notes=progress_notes or None,
    )
    entry = build_normalized_entry(payload, source="web_form")

    logger.info("Submitting entry via web form project=%s category=%s", project, category)
    try:
        item_id = await graph_client.upload_entry(entry)
    except Exception as exc:  # pragma: no cover - simple error mapping
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload to SharePoint: {exc}",
        ) from exc

    IN_MEMORY_ENTRIES.append(entry)
    await _record_ledger_for_entry(entry, item_id=item_id, source="web_form")

    return RedirectResponse(url="/entries", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/api/entries", response_model=EntryNormalized)
async def create_entry_api(payload: EntryCreate) -> EntryNormalized:
    entry = build_normalized_entry(payload, source="api")

    logger.info("API entry submission project=%s category=%s", payload.project, payload.category)
    try:
        item_id = await graph_client.upload_entry(entry)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload to SharePoint: {exc}",
        ) from exc

    IN_MEMORY_ENTRIES.append(entry)
    await _record_ledger_for_entry(entry, item_id=item_id, source="api")
    return entry


@app.post("/api/projects/{project_name}/progress", response_model=EntryNormalized)
async def log_project_progress(
    project_name: str,
    stage: str,
    note: str,
) -> EntryNormalized:
    """
    Built-in convention endpoint for project progress logging.

    This wraps the generic entry creation with:
      - category=progress
      - project derived from the path
      - stage + note captured in dedicated fields
    """
    payload = EntryCreate(
        project=project_name,
        category=EntryCategory.PROGRESS,
        content_raw=note,
        tags=[],
        progress_stage=stage,
        progress_notes=note,
    )
    entry = build_normalized_entry(payload, source="api-progress")

    logger.info(
        "Progress entry submission project=%s stage=%s", project_name, stage
    )
    try:
        item_id = await graph_client.upload_entry(entry)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload to SharePoint: {exc}",
        ) from exc

    IN_MEMORY_ENTRIES.append(entry)
    await _record_ledger_for_entry(entry, item_id=item_id, source="api-progress")
    return entry


@app.get("/health")
async def health() -> dict:
    """
    Basic health check including Graph connectivity.
    """
    graph_ok = False
    try:
        graph_ok = await graph_client.health_check()
    except Exception:
        graph_ok = False

    outcome = {
        "status": "ok" if graph_ok else "degraded",
        "graph": "ok" if graph_ok else "unreachable",
    }
    logger.info("Health check result: %s", outcome)
    return outcome
