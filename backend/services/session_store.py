"""
In-memory store for active interview sessions.

A FastAPI request is stateless, but an interview spans many requests
(start, then one /answer call per turn). This module holds the live
`InterviewController` and conversation state per candidate for the
duration of their interview.

NOTE: this only works for a SINGLE-PROCESS deployment (one `uvicorn`
worker, no horizontal scaling). If you later run multiple worker
processes or multiple machines, replace this with a shared store (Redis,
a database row, etc.) — the get/start/update/end interface below is
designed to make that swap a drop-in change without touching the routes.
"""

from typing import Dict, Optional, Any
import threading

_SESSIONS: Dict[str, dict] = {}
_lock = threading.Lock()


def start_session(candidate_id: str, controller) -> None:
    with _lock:
        _SESSIONS[candidate_id] = {
            "controller": controller,
            "conversation_history": [],
            "interview_log": [],
            "last_evaluation": None,
            "was_terminated": False,
            "termination_reason": None,
            "pending_directive": None,
            "pending_output": None,
        }


def get_session(candidate_id: str) -> Optional[dict]:
    return _SESSIONS.get(candidate_id)


def update_session(candidate_id: str, **fields: Any) -> None:
    with _lock:
        if candidate_id in _SESSIONS:
            _SESSIONS[candidate_id].update(fields)


def end_session(candidate_id: str) -> None:
    with _lock:
        _SESSIONS.pop(candidate_id, None)
