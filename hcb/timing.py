"""P-16 (2026-11-28): minutes per phase of a document preparation, measured by code (task make -> validate, engine
runs), so speed changes are judged with data. Events kind="phase" in events.jsonl."""
from __future__ import annotations

from datetime import datetime
from statistics import median

from . import state


def record(task_id: str, role: str, action: str, seconds: float, outcome: str = "") -> dict:
    return state.event("phase", task_id=task_id, role=role, action=action, seconds=round(seconds, 1), outcome=outcome)


def since(iso: str) -> float:
    try:
        return max(0.0, (datetime.now().astimezone() - datetime.fromisoformat(iso)).total_seconds())
    except (TypeError, ValueError):
        return 0.0


def recent(n: int = 10) -> dict:
    """Median minutes per role/action over the last n phase events of each; the last preparation's phases."""
    rows = [e for e in state._read("events.jsonl") if e.get("kind") == "phase"]
    by: dict = {}
    for e in rows:
        by.setdefault(f"{e.get('role')}:{e.get('action')}", []).append(float(e.get("seconds") or 0))
    med = {k: round(median(v[-n:]) / 60, 1) for k, v in by.items()}
    return {"median_minutes": med, "last": [{k: e.get(k) for k in ("at", "role", "action", "seconds", "outcome")}
                                            for e in rows[-8:]]}
