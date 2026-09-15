"""
Simple JSON-file-backed candidate registry — powers the Admin dashboard's
candidate list (including Disqualified candidates who never got an
interview).

NOTE: this is intentionally simple (a single JSON file + a lock) for an
initial backend-only deployment. For production with real concurrent
traffic, replace this with a proper database table — the function
signatures below (create/update/get/list) are designed to make that swap
straightforward later without touching the routes that call them.
"""

import json
import os
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

INDEX_PATH = "data/candidates_index.json"
_lock = threading.Lock()


def _load_index() -> dict:
    if not os.path.exists(INDEX_PATH):
        return {}
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_index(index: dict):
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


def create_candidate(candidate_id: str, name: str):
    with _lock:
        index = _load_index()
        index[candidate_id] = {
            "candidate_id": candidate_id,
            "name": name,
            "status": "Screening",
            "requirement_match_score": None,
            "interview_performance_score": None,
            "combined_score": None,
            "recommendation": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_index(index)


def update_candidate(candidate_id: str, **fields: Any):
    with _lock:
        index = _load_index()
        if candidate_id not in index:
            index[candidate_id] = {"candidate_id": candidate_id}
        index[candidate_id].update(fields)
        index[candidate_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_index(index)


def get_candidate(candidate_id: str) -> Optional[Dict[str, Any]]:
    return _load_index().get(candidate_id)


def list_candidates() -> List[Dict[str, Any]]:
    index = _load_index()
    return sorted(index.values(), key=lambda c: c.get("created_at", ""), reverse=True)
