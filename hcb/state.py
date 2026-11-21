"""Append-only audit trail: events, approvals, idempotency ledger, task records.

Answers Master §10.4 ("what task started and why, which approval enabled it, which
records changed, which errors occurred") without reading model reasoning.
Files live in state/ (git-ignored). Nothing here stores secrets.
"""
from __future__ import annotations

import json
from pathlib import Path

from .util import dump, now_iso, project_path, redact, stable_key

TASK_STATES = {"pending", "running", "completed", "failed", "blocked", "cancelled", "partially_delivered"}
# Retry-safe transitions (Master §8.4). An uncertain external write is never retried blindly.
RETRYABLE = {("failed", "pending"), ("blocked", "pending")}


def _append(name: str, record: dict) -> dict:
    record = {"at": now_iso(), **record}
    with (project_path("state") / name).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _read(name: str) -> list[dict]:
    path = project_path("state") / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def event(kind: str, **fields) -> dict:
    if "message" in fields:
        fields["message"] = redact(fields["message"])
    return _append("events.jsonl", {"kind": kind, **fields})


def error_event(process: str, task_id: str, role: str, category: str, message: str,
                attempts: int, effect: str, unaffected: list, recovery: str, action_required: str) -> dict:
    """Master §6.8 Error Event."""
    return event("error", process=process, task_id=task_id, role=role, category=category,
                 message=message, attempts=attempts, effect=effect, unaffected_work=unaffected,
                 recovery_state=recovery, action_required=action_required)


def record_approval(actor: str, action: str, objects: list, channel: str, scope: str,
                    source_message_ref: str, expiry: str | None = None) -> dict:
    """project-manager.md §6.4.10. Only the PM records approvals, from a user message."""
    approval_id = "AP-" + stable_key(actor, action, ",".join(map(str, objects)), source_message_ref)
    existing = find_approval(approval_id=approval_id)
    if existing:
        return existing
    return _append("approvals.jsonl", {"approval_id": approval_id, "actor": actor, "action": action,
                                       "objects": [str(o) for o in objects], "channel": channel,
                                       "scope": scope, "expiry": expiry,
                                       "source_message_ref": source_message_ref})


def find_approval(approval_id: str | None = None, action: str | None = None, obj: str | None = None) -> dict | None:
    for rec in reversed(_read("approvals.jsonl")):
        if approval_id and rec["approval_id"] != approval_id:
            continue
        if action and rec["action"] != action:
            continue
        if obj is not None and str(obj) not in rec["objects"]:
            continue
        return rec
    return None


def require_approval(action: str, obj: str) -> dict:
    """Gate implemented in the tool, not only in instructions (project-manager.md §5).
    An approval never extends to another action by similarity (Master §9.2)."""
    rec = find_approval(action=action, obj=obj)
    if rec is None:
        raise PermissionError(f"No approval record for action={action!r} object={obj!r}")
    return rec


def ledger_get(key: str) -> dict | None:
    for rec in reversed(_read("ledger.jsonl")):
        if rec["idempotency_key"] == key:
            return rec
    return None


def ledger_put(key: str, effect: str, result_ref: str, status: str) -> dict:
    return _append("ledger.jsonl", {"idempotency_key": key, "effect": effect,
                                    "result_ref": result_ref, "status": status})


def save_task(task: dict) -> Path:
    assert task["status"] in TASK_STATES, task["status"]
    path = project_path("state") / "tasks" / f"{task['task_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(task), encoding="utf-8")
    event("task_state", task_id=task["task_id"], role=task.get("role"), action=task.get("action"),
          status=task["status"])
    return path


def load_task(task_id: str) -> dict | None:
    path = project_path("state") / "tasks" / f"{task_id}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
