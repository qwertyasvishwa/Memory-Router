"""
Helper script to launch the Memory Router FastAPI app with explicit options.

This is useful when wrapping the service with process managers (Windows Service,
NSSM, etc.) because you can point the manager at this script instead of typing
the uvicorn arguments directly.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Memory Router via uvicorn.")
    parser.add_argument("--host", default=os.environ.get("MR_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MR_PORT", 8000)))
    parser.add_argument(
        "--log-level",
        default=os.environ.get("MR_LOG_LEVEL", "info"),
        choices=["critical", "error", "warning", "info", "debug", "trace"],
    )
    parser.add_argument(
        "--reload",
        dest="reload",
        action="store_true",
        help="Enable uvicorn reload (not recommended for Windows services).",
    )
    parser.add_argument(
        "--no-reload",
        dest="reload",
        action="store_false",
        help="Disable uvicorn reload (default).",
    )
    parser.set_defaults(reload=False)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
