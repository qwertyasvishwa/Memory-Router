import logging
from typing import List

from .schemas import (
    LedgerEntryCreate,
    LedgerEntryNormalized,
    build_ledger_entry,
)
from .sharepoint_client import graph_client

logger = logging.getLogger(__name__)


class LedgerService:
    """
    Handles creation + upload of structured ledger entries.

    Entries are uploaded as JSON into the same SharePoint folder hierarchy,
    under a `ledger/` subfolder (further partitioned by year/month).
    """

    def __init__(self) -> None:
        self._in_memory: List[LedgerEntryNormalized] = []

    async def log_entry(
        self,
        payload: LedgerEntryCreate,
        *,
        source: str,
        actor: str | None = None,
    ) -> LedgerEntryNormalized:
        entry = build_ledger_entry(payload, source=source, actor=actor)
        year_month = entry.month_tag
        filename = f"{entry.created_at.isoformat().replace(':', '-')}_{entry.id}.json"
        subfolder = f"ledger/{year_month}"

        await graph_client.upload_json_document(
            entry.model_dump(mode="json"),
            filename=filename,
            subfolder=subfolder,
        )

        self._in_memory.append(entry)
        logger.info(
            "Ledger entry recorded id=%s theme=%s lens=%s",
            entry.id,
            entry.theme,
            entry.lens,
        )
        return entry

    def list_entries(self) -> List[LedgerEntryNormalized]:
        return sorted(self._in_memory, key=lambda e: e.created_at, reverse=True)


ledger_service = LedgerService()
