"""
In-memory pipeline status for frontend display.
Updated by pipeline tasks, read by GET /api/pipeline/status.
"""

import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any

_lock = threading.Lock()
_status: Dict[str, Any] = {
    "running": False,
    "task": None,  # "scrape" | "analyze" | "full"
    "message": "",
    "progress": None,  # {"current": int, "total": int}
    "started_at": None,
    "finished_at": None,
}


def set_running(task: str, message: str = "", progress: Optional[Dict[str, int]] = None) -> None:
    """Mark pipeline as running with current task info."""
    with _lock:
        _status["running"] = True
        _status["task"] = task
        _status["message"] = message
        _status["progress"] = progress
        _status["started_at"] = datetime.now(timezone.utc).isoformat()
        _status["finished_at"] = None


def update_progress(message: str, current: int, total: int) -> None:
    """Update progress during a running task."""
    with _lock:
        _status["message"] = message
        _status["progress"] = {"current": current, "total": total}


def set_idle() -> None:
    """Mark pipeline as idle (finished or not started)."""
    with _lock:
        _status["running"] = False
        _status["task"] = None
        _status["message"] = ""
        _status["progress"] = None
        _status["finished_at"] = datetime.now(timezone.utc).isoformat()


def get_status() -> Dict[str, Any]:
    """Return current status (for API)."""
    with _lock:
        return {
            "running": _status["running"],
            "task": _status["task"],
            "message": _status["message"],
            "progress": _status["progress"],
            "started_at": _status["started_at"],
            "finished_at": _status["finished_at"],
        }
