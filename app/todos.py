import logging
from typing import List

from .schemas import TodoEntryCreate, TodoEntryNormalized, build_todo_entry
from .sharepoint_client import graph_client

logger = logging.getLogger(__name__)


class TodoService:
    """
    Lightweight task tracker stored directly in SharePoint under
    Memory Router/todos/<YYYY-MM>/....
    """

    def __init__(self) -> None:
        self._entries: List[TodoEntryNormalized] = []

    async def add_entry(self, payload: TodoEntryCreate) -> TodoEntryNormalized:
        entry = build_todo_entry(payload)
        filename = f"{entry.created_at.isoformat().replace(':', '-')}_{entry.id}.json"
        subfolder = f"todos/{entry.month_tag}"

        await graph_client.upload_json_document(
            entry.model_dump(mode="json"),
            filename=filename,
            subfolder=subfolder,
        )

        self._entries.append(entry)
        logger.info("Todo entry recorded id=%s title=%s", entry.id, entry.title)
        return entry

    def list_entries(self) -> List[TodoEntryNormalized]:
        return sorted(self._entries, key=lambda e: (e.status, -e.created_at.timestamp()))


todo_service = TodoService()
