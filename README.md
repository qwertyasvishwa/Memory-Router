# Memory Router – FastAPI + SharePoint (Graph)

This project is a minimal FastAPI service that:

- accepts text entries via web form or JSON API
- normalizes them into a stable JSON schema
- uploads each entry directly as JSON into a SharePoint/OneDrive drive using Microsoft Graph
- keeps a session-only in-memory list for quick browsing
- exposes a health endpoint (including a Graph connectivity check)
- provides a built-in convention for project progress logging
- includes a SharePoint drive browser so you can explore any accessible drive, download files, and switch drives dynamically

There is **no local database** and **no local filesystem writes** – entries go straight to Microsoft Graph.

> AI note: this service does **not** call any external LLM / GPT APIs. You can freely use VS Code Copilot or other built-in AI tooling while working on the code; they are editor-side helpers only.

## Quick start

1. Create and activate a Python virtual environment (3.11+ recommended).

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables (or a `.env` file in the repo root) for Microsoft Graph:

   - `MR_TENANT_ID` – Azure AD tenant ID
   - `MR_CLIENT_ID` – app registration client ID
   - `MR_CLIENT_SECRET` – app registration client secret
   - `MR_DRIVE_ID` – target drive ID where JSON files will be written
   - `MR_FOLDER_PATH` – folder path under the drive root (default: `MemoryRouter`)

   These are used by `app/config.py` and `app/sharepoint_client.py`. The app uses **client credentials (app-only)** authentication.

4. Run the service:

   ```bash
   uvicorn app.main:app --reload
   ```

5. Open the UI:

   - Web form: `http://localhost:8000/`
   - Session browse view: `http://localhost:8000/entries`
   - Health check: `http://localhost:8000/health`

### Keep the server running as a Windows Service

If you want Memory Router to keep running after you close the terminal, one straightforward approach on Windows is to use [NSSM](https://nssm.cc/).

1. Download `nssm-2.24.zip`, extract it (e.g., `C:\tools\nssm-2.24\win64\nssm.exe`).
2. Install the service from an elevated PowerShell prompt:

   ```powershell
   $python = (Get-Command python).Source
   $nssm   = 'C:\tools\nssm-2.24\win64\nssm.exe'          # adjust if needed
   $wd     = 'C:\Users\<you>\Documents\Project\Memory-Router'

   & $nssm install MemoryRouter $python "$wd\scripts\run_server.py --host 0.0.0.0 --port 8000 --log-level info"
   & $nssm set MemoryRouter AppDirectory $wd
   Set-Service MemoryRouter -StartupType Automatic
   Start-Service MemoryRouter
   ```

The `scripts/run_server.py` helper ensures the working directory is correct and lets you tweak host/port/log level later. Stop/restart with `Stop-Service MemoryRouter` / `Start-Service MemoryRouter`.

## API overview

- `GET /` – HTML form for submitting a new entry.
- `POST /submit` – form handler; normalizes and uploads to SharePoint.
- `GET /entries` – HTML view of entries accepted during the current process lifetime (in-memory only).
- `GET /api/entries` – JSON list of in-memory entries.
- `POST /api/entries` – JSON API to submit a new entry.
- `POST /api/projects/{project_name}/progress` – shortcut endpoint for project progress logging.
- `GET /drive` – SharePoint drive browser (choose any drive ID you have access to, browse folders, download files).
- `GET /api/drive/children` – list items in a drive/folder (`drive_id` + `path` query params).
- `GET /api/drives` – enumerate drives the service principal can reach (includes configured drive, `/me/drives`, and optional site drives).
- `GET /drive/download/{item_id}` – download a file directly from the selected drive.
- `GET /ledger` – Memory Ledger UI for structured progress logging with Theme/Lens/Tag fields.
- `POST /ledger` – HTML form handler for manual ledger entries.
- `GET /api/ledger` / `POST /api/ledger` – JSON API for listing/creating ledger entries programmatically.
- `POST /todos` – HTML form for next-action logging (tasks/milestones).
- `GET /api/todos` / `POST /api/todos` – JSON API for lightweight task tracking.
- `GET /health` – health and Graph connectivity status.

### Logging

The service logs to stdout/stderr (captured in `/tmp/uvicorn.log` in these instructions) with contextual messages whenever entries are submitted, drives are listed, downloads occur, or health checks run. Adjust the log level by editing the `logging.basicConfig` call in `app/main.py`.

### Memory Ledger (structured progress logging)

- Schema lives in `app/schemas.py` (`LedgerEntry*` models). Every entry includes Theme, Lens, Value tags (#HumanTouch, #Integrity, etc.), artifact tags (#WorkflowDecision, #Demo, etc.), references, and auto-generated tags (#Theme/<value>, #Lens/<value>, #Month/YYYY-MM).
- `app/ledger.py` writes each entry as JSON into your configured SharePoint drive under `Memory Router/ledger/<YYYY-MM>/...`. No local storage.
- The `/ledger` page lets you capture quick notes; API endpoints support automation (weekly digests, release notes, etc.).
- Entry submissions (web + API) automatically append ledger records so you always know what was captured, by whom, and why.

### Quick links + Todo tracker

- The home page now shows curated quick links (edit `QUICK_LINKS` in `app/main.py`).
- A lightweight todo/milestone section lets you jot down next steps; everything is written to SharePoint under `Memory Router/todos/<YYYY-MM>/...`.
- Endpoints `/api/todos` and `/todos` enable automation or scripting (e.g., capture tasks from CLI, generate milestone digests).

### JSON schema (normalized entries)

All entries are normalized into a stable schema (see `app/schemas.py`):

- `id` – UUID (string)
- `created_at` – UTC timestamp when accepted
- `project` – optional project name
- `category` – `"note"` or `"progress"`
- `content_raw` – original text
- `content_normalized` – normalized text (trimmed, line endings, blank-line collapsing)
- `tags` – list of strings
- `progress_stage` – optional stage/phase name for progress entries
- `progress_notes` – optional structured progress note
- `source` – `"web_form"`, `"api"`, or `"api-progress"`

Each entry is stored as a standalone `.json` file in the configured SharePoint/OneDrive drive.

## What I still need from you

To fully wire this into your SharePoint environment, please provide:

- The **Graph drive ID** where you want the JSON files stored (or, if you prefer, the target SharePoint site + document library so we can derive the drive).
- The **folder path** under that drive root (if different from the default `MemoryRouter`).
- Confirmation that you will use **app-only (client credentials)** auth for the Graph app registration (this is what the code assumes).

Once I have those details, I can:

- fine-tune the Graph endpoints if your setup uses sites/lists instead of a drive, and
- optionally add a helper script or notes for how to retrieve the drive ID from your tenant.
