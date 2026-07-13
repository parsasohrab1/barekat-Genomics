"""اجرای ابزارهای خط فرمان bioinformatics."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class ToolNotFoundError(RuntimeError):
    pass


class CommandFailedError(RuntimeError):
    pass


def tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def require_tools(*names: str) -> None:
    missing = [n for n in names if not tool_available(n)]
    if missing:
        raise ToolNotFoundError(f"ابزارهای یافت‌نشده: {', '.join(missing)}")


def run_command(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    logger.info("running_command", extra={"cmd": " ".join(cmd), "cwd": str(cwd) if cwd else None})
    merged_env = {**os.environ, **(env or {})}
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=merged_env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CommandFailedError(f"Timeout: {' '.join(cmd)}") from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or f"exit code {result.returncode}"
        raise CommandFailedError(f"{' '.join(cmd)} failed: {detail}")

    return result


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
