from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


class GitError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitCommandResult:
    args: List[str]
    cwd: str
    returncode: int
    stdout: str
    stderr: str


def _safe_repo_path(repo_path: str | Path) -> Path:
    p = Path(repo_path).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        raise GitError(f"Repo path does not exist: {p}")
    if not (p / ".git").exists():
        raise GitError(f"Not a git repository (missing .git): {p}")
    return p


def _run_git(
    repo: Path,
    args: List[str],
    *,
    timeout_s: int = 60,
    env: Optional[Dict[str, str]] = None,
) -> GitCommandResult:
    cmd = ["git", *args]
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    proc = subprocess.run(
        cmd,
        cwd=str(repo),
        env=merged_env,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return GitCommandResult(
        args=cmd,
        cwd=str(repo),
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


def _require_ok(res: GitCommandResult) -> GitCommandResult:
    if res.returncode != 0:
        msg = res.stderr.strip() or res.stdout.strip() or "git command failed"
        raise GitError(msg)
    return res


def git_available() -> bool:
    try:
        res = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=10)
        return res.returncode == 0
    except Exception:
        return False


def get_status(repo_path: str | Path) -> dict:
    repo = _safe_repo_path(repo_path)
    _require_ok(_run_git(repo, ["rev-parse", "--is-inside-work-tree"]))

    branch_res = _run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch_res.stdout.strip() if branch_res.returncode == 0 else "(unknown)"

    porcelain = _require_ok(_run_git(repo, ["status", "--porcelain=v1"]))
    clean = porcelain.stdout.strip() == ""

    ahead_behind_res = _run_git(repo, ["rev-list", "--left-right", "--count", "HEAD...@{upstream}"])
    ahead = behind = None
    if ahead_behind_res.returncode == 0:
        parts = ahead_behind_res.stdout.strip().split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])

    return {
        "repo": str(repo),
        "branch": branch,
        "clean": clean,
        "porcelain": porcelain.stdout,
        "ahead": ahead,
        "behind": behind,
    }


def fetch(repo_path: str | Path, *, remote: str = "origin") -> dict:
    repo = _safe_repo_path(repo_path)
    res = _require_ok(_run_git(repo, ["fetch", "--prune", remote], timeout_s=120))
    return {"ok": True, "stdout": res.stdout, "stderr": res.stderr}


def pull_rebase(repo_path: str | Path, *, remote: str = "origin") -> dict:
    """Pull using rebase. Never auto-resolves conflicts.

    If conflicts occur, git returns non-zero and caller must resolve manually.
    """
    repo = _safe_repo_path(repo_path)

    # Ensure upstream exists; otherwise provide a friendly error.
    upstream = _run_git(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"])
    if upstream.returncode != 0:
        raise GitError(
            "No upstream configured for current branch. Set it with: "
            "git push -u origin <branch>"
        )

    res = _run_git(repo, ["pull", "--rebase", remote], timeout_s=300)
    if res.returncode != 0:
        # Provide a little extra help for common conflict state.
        conflict_hint = ""
        if "CONFLICT" in (res.stdout + res.stderr):
            conflict_hint = (
                "\nConflicts detected. Resolve them, then run: "
                "git rebase --continue (or git rebase --abort to cancel)."
            )
        raise GitError((res.stderr.strip() or res.stdout.strip() or "git pull failed") + conflict_hint)

    return {"ok": True, "stdout": res.stdout, "stderr": res.stderr}


def push(repo_path: str | Path, *, remote: str = "origin") -> dict:
    repo = _safe_repo_path(repo_path)
    res = _run_git(repo, ["push", remote], timeout_s=300)
    if res.returncode != 0:
        raise GitError(res.stderr.strip() or res.stdout.strip() or "git push failed")
    return {"ok": True, "stdout": res.stdout, "stderr": res.stderr}


def conflict_files(repo_path: str | Path) -> List[str]:
    repo = _safe_repo_path(repo_path)
    res = _require_ok(_run_git(repo, ["diff", "--name-only", "--diff-filter=U"]))
    files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    return files


def conflict_markers_preview(repo_path: str | Path, rel_path: str, *, max_lines: int = 200) -> str:
    repo = _safe_repo_path(repo_path)
    target = (repo / rel_path).resolve()
    if repo not in target.parents and target != repo:
        raise GitError("Invalid path")
    if not target.exists() or not target.is_file():
        raise GitError(f"File not found: {rel_path}")

    # Only show a small preview to avoid dumping large files.
    lines: List[str] = []
    with target.open("r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if i >= max_lines:
                lines.append("... (truncated)\n")
                break
            lines.append(line)

    return "".join(lines)
