import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx
import msal

from .config import get_settings
from .schemas import EntryNormalized

logger = logging.getLogger(__name__)

class GraphClient:
    """
    Minimal Microsoft Graph client for uploading normalized entries into a drive.

    This client:
      - uses client credentials (app-only) auth via MSAL
      - uploads each entry as a standalone JSON file into a configured folder
      - does not touch local disk or any database
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._app = msal.ConfidentialClientApplication(
            client_id=self.settings.client_id,
            client_credential=self.settings.client_secret,
            authority=f"https://login.microsoftonline.com/{self.settings.tenant_id}",
        )

    def _acquire_token(self) -> str:
        result = self._app.acquire_token_silent(
            scopes=["https://graph.microsoft.com/.default"],
            account=None,
        )
        if not result:
            result = self._app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"],
            )
        if "access_token" not in result:
            error = result.get("error_description", "unknown error")
            logger.error("Graph token acquisition failed: %s", error)
            raise RuntimeError(f"Could not acquire Graph token: {error}")
        return str(result["access_token"])

    def _compose_path(self, filename: str, subfolder: Optional[str] = None) -> str:
        base = self.settings.folder_path.strip("/ ")
        pieces = [segment for segment in [base, subfolder.strip("/ ") if subfolder else None, filename] if segment]
        return "/".join(pieces) if pieces else filename

    async def _upload_bytes(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
        subfolder: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> str:
        token = self._acquire_token()
        drive = self._resolve_drive(drive_id)
        path = self._compose_path(filename, subfolder=subfolder)

        url = (
            f"https://graph.microsoft.com/v1.0"
            f"/drives/{drive}/root:/{path}:/content"
        )

        logger.info("Uploading document to drive=%s path=%s", drive, path)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.put(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": content_type,
                },
                content=content,
            )
            response.raise_for_status()

        data = response.json()
        item_id = str(data.get("id"))
        logger.info("Uploaded document path=%s item=%s", path, item_id)
        return item_id

    async def upload_json_document(
        self,
        payload: Dict[str, Any],
        *,
        filename: str,
        subfolder: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> str:
        return await self._upload_bytes(
            content=json.dumps(payload).encode("utf-8"),
            filename=filename,
            content_type="application/json",
            subfolder=subfolder,
            drive_id=drive_id,
        )

    async def upload_text_document(
        self,
        content: str,
        *,
        filename: str,
        subfolder: Optional[str] = None,
        drive_id: Optional[str] = None,
        content_type: str = "text/markdown",
    ) -> str:
        return await self._upload_bytes(
            content=content.encode("utf-8"),
            filename=filename,
            content_type=content_type,
            subfolder=subfolder,
            drive_id=drive_id,
        )

    async def upload_entry(self, entry: EntryNormalized) -> str:
        """
        Upload a single normalized entry as JSON to the configured drive (under the configured folder).
        """
        filename = f"{entry.created_at.isoformat().replace(':', '-')}_{entry.id}.json"
        return await self.upload_json_document(
            entry.model_dump(mode="json"),
            filename=filename,
            subfolder=None,
        )

    def _resolve_drive(self, drive_id: Optional[str]) -> str:
        return drive_id or self.settings.drive_id

    async def list_children(
        self,
        path: str | None = None,
        *,
        drive_id: str | None = None,
        base_folder: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List items under the given path in the configured drive.

        If path is None or empty, lists the root of MR_FOLDER_PATH (or drive root
        if MR_FOLDER_PATH is empty).
        """
        token = self._acquire_token()
        drive = self._resolve_drive(drive_id)
        base_config = self.settings.folder_path.strip("/ ")
        base_path = (base_folder if base_folder is not None else base_config).strip("/ ")

        if path:
            target_path = f"{base_path}/{path.lstrip('/')}" if base_path else path.lstrip("/")
        else:
            target_path = base_path

        if target_path:
            url = (
                "https://graph.microsoft.com/v1.0"
                f"/drives/{drive}/root:/{target_path}:/children"
            )
        else:
            url = f"https://graph.microsoft.com/v1.0/drives/{drive}/root/children"

        logger.debug(
            "Listing children in drive=%s base=%s path=%s target=%s",
            drive,
            base_path,
            path,
            target_path or "/",
        )
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()

        data = response.json()
        items = data.get("value", [])
        logger.info(
            "Listed %d items for drive=%s path=%s",
            len(items),
            drive,
            target_path or "/",
        )
        return items

    async def list_available_drives(self) -> List[Dict[str, Any]]:
        """
        Return drives the service principal can access.

        We query:
          - the configured drive (so it always shows up)
          - /me/drives (OneDrive + SharePoint favorites for the signed-in account)
          - optionally the configured site (if site_id provided)
        """
        token = self._acquire_token()
        headers = {"Authorization": f"Bearer {token}"}
        drives: dict[str, Dict[str, Any]] = {}

        async with httpx.AsyncClient(timeout=20.0) as client:
            # Ensure configured drive is included
            try:
                resp = await client.get(
                    f"https://graph.microsoft.com/v1.0/drives/{self.settings.drive_id}",
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    drives[str(data.get("id"))] = data
            except Exception:
                pass

            endpoints = [
                "https://graph.microsoft.com/v1.0/me/drives",
            ]
            if self.settings.site_id:
                endpoints.append(
                    f"https://graph.microsoft.com/v1.0/sites/{self.settings.site_id}/drives"
                )

            for url in endpoints:
                try:
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    for drive in resp.json().get("value", []):
                        drives[str(drive.get("id"))] = drive
                except httpx.HTTPStatusError:
                    continue

        drive_list = list(drives.values())
        logger.info("Discovered %d drives accessible to the app", len(drive_list))
        return drive_list

    async def download_item(
        self,
        item_id: str,
        *,
        drive_id: str | None = None,
    ) -> Tuple[bytes, str, str]:
        """
        Download a drive item (file) and return its bytes, content type, and name.
        """
        token = self._acquire_token()
        drive = self._resolve_drive(drive_id)

        metadata_url = f"https://graph.microsoft.com/v1.0/drives/{drive}/items/{item_id}"
        content_url = f"{metadata_url}/content"

        logger.info("Downloading drive item %s from drive %s", item_id, drive)
        async with httpx.AsyncClient(timeout=30.0) as client:
            meta_resp = await client.get(metadata_url, headers={"Authorization": f"Bearer {token}"})
            meta_resp.raise_for_status()
            meta = meta_resp.json()
            name = str(meta.get("name", "download.bin"))

            content_resp = await client.get(
                content_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            content_resp.raise_for_status()
            content_type = content_resp.headers.get("Content-Type", "application/octet-stream")
            logger.info("Downloaded %s (%s bytes)", name, len(content_resp.content))
            return content_resp.content, content_type, name

    async def health_check(self) -> bool:
        """
        Lightweight Graph health check.

        This checks that:
          - we can obtain a token
          - the configured drive is reachable
        """
        token = self._acquire_token()
        url = f"https://graph.microsoft.com/v1.0/drives/{self.settings.drive_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code == 200:
                return True
        return False


graph_client = GraphClient()
