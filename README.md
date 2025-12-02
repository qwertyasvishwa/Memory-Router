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

   **Development mode (with auto-reload):**
   ```powershell
   # Using the management wrapper (recommended)
   .\scripts\manage_service.ps1 start

   # Or directly with uvicorn
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

   **Production mode:**
   ```powershell
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

5. Open the UI:

   - Web form: `http://localhost:8000/`
   - Session browse view: `http://localhost:8000/entries`
   - Weekly task tracker: `http://localhost:8000/weekly-tasks`
   - Health check: `http://localhost:8000/health`

## Development Scripts

The `scripts/` folder contains PowerShell utilities for managing the development server:

- **`manage_service.ps1`** - Main wrapper for start/stop/restart/status operations
- **`start_dev_server.ps1`** - Starts uvicorn with --reload and writes PID to server.pid
- **`stop_dev_server.ps1`** - Stops the server and cleans up PID file

### Development Commands

```powershell
# Start server with auto-reload
.\scripts\manage_service.ps1 start

# Check server status
.\scripts\manage_service.ps1 status

# Restart server
.\scripts\manage_service.ps1 restart

# Stop server
.\scripts\manage_service.ps1 stop
```

**Note:** If you encounter socket permission errors (WinError 10013) on port 8000, try:
- Check for conflicting processes: `netstat -ano | Select-String ':8000'`
- Start on alternate port: `.\scripts\manage_service.ps1 start -Port 8081`

### Keep the server running as a Windows Service

For production deployments, use [NSSM](https://nssm.cc/) to run Memory Router as a Windows service:

1. Download `nssm-2.24.zip`, extract it (e.g., `C:\tools\nssm-2.24\win64\nssm.exe`).

2. Install the service using the management script (from elevated PowerShell):

   ```powershell
   # Install NSSM service
   .\scripts\manage_service.ps1 install-nssm -NssmPath "C:\tools\nssm-2.24\win64\nssm.exe"

   # Start the service
   Start-Service MemoryRouter

   # Set to start automatically
   Set-Service MemoryRouter -StartupType Automatic
   ```

3. Service management:

   ```powershell
   # Start/stop the service
   Start-Service MemoryRouter
   Stop-Service MemoryRouter

   # Check service status
   Get-Service MemoryRouter

   # Uninstall service (if needed)
   .\scripts\manage_service.ps1 uninstall-nssm -NssmPath "C:\tools\nssm-2.24\win64\nssm.exe"
   ```

**Important:** The NSSM service runs without `--reload` for stability. Service logs are written to `server-out.log` and `server-err.log` in the project root.

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

## Weekly Task Tracker

The new weekly task tracker accepts product updates or notes via `/weekly-tasks` and responds with macro-level action items plus a dedicated "overlooked or missing tasks" section. It deduplicates every generated task and logs the run to `weekly_tasks_log.csv` so nothing is repeated unless the scope evolves.

- Use the form on `/weekly-tasks` or call `POST /api/weekly-tasks` with `{ "project": "...", "context": "...", "update": "..." }`.
- Review prior tracker outputs via the UI table (now highlighting the latest entry after each submission) or `GET /api/weekly-tasks/history?limit=20`.
- Tasks are deduplicated per project and ISO week, so reminders can resurface once you move into a new week or project without rewriting previous guidance.
- The CSV log lives wherever `MR_WEEKLY_LOG_PATH` points (defaults to `weekly_tasks_log.csv` in the repo root) and is ignored by git so you can keep a persistent audit trail of tracked tasks.
- Upload `.msg`/`.eml` Outlook updates directly into the tracker UI and click **Export full report to SharePoint** to create a Markdown snapshot under `reports/weekly-tracker/` in your configured drive.
- Every entry captures an `activity_type` (`campaign_execution`, `product_design`, `engineering_delivery`, `training_enablement`, `ops_compliance`, `performance_reporting`). Filter the weekly list by project or activity type from the UI to zero in on specific workstreams.

## Enhancement log + recommendations

Use `/enhancements` (or `POST /api/enhancements`) to record every change you ship, including the reason and expected impact. The service appends each entry to the CSV pointed to by `MR_ENHANCEMENT_LOG_PATH` (default `enhancements_log.csv`) and surfaces tailored improvement ideas via `/api/enhancements/suggestions`. Suggestions look at recent reasons, untouched areas, and high-signal tags to recommend the next best initiative.

- Click **Export enhancement report to SharePoint** to publish a Markdown changelog (under `reports/enhancements/`) that captures every logged change with timestamps and references.

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
