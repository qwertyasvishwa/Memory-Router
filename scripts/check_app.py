import os
import pathlib
import sys


def ensure_settings() -> None:
    """Seed the minimal required MR_* environment variables with placeholders."""
    os.environ.setdefault("MR_TENANT_ID", "common")
    os.environ.setdefault("MR_CLIENT_ID", "placeholder-client")
    os.environ.setdefault("MR_CLIENT_SECRET", "placeholder-secret")
    os.environ.setdefault("MR_DRIVE_ID", "placeholder-drive")
    os.environ.setdefault("MR_FOLDER_PATH", "MemoryRouter")


def ensure_project_path() -> None:
    """Make sure the project root is on sys.path for local module imports."""
    project_root = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))


if __name__ == "__main__":
    ensure_settings()
    ensure_project_path()

    from app.main import app  # noqa: E402

    print("FastAPI app imported successfully with", len(app.routes), "routes.")
