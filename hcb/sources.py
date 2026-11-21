"""Which enabled sources a search run must read (config/sources.yaml cadences).

Deterministic so the Job Hunter never re-reads every site on every run:
- every_run            -> each of the three weekday runs (07:30, 12:30, 16:30);
- first_run:<days>     -> only the first run (before 10:00) on those weekdays.
Only `enabled: true` + `mode: page_read` sources are ever returned (AP-338e1986beb43f61360209de).
"""
from __future__ import annotations

from datetime import datetime

from .util import ROOT, load_yaml

_DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
FIRST_RUN_BEFORE_HOUR = 10
MIN_GAP_S = 20


def registry() -> list[dict]:
    return load_yaml(ROOT / "config" / "sources.yaml")["sources"]


def due(now: datetime) -> dict:
    if now.weekday() > 4:
        return {"run": [], "reason": "weekend: no search (D-USR-02)"}
    first = now.hour < FIRST_RUN_BEFORE_HOUR
    run, skipped = [], []
    for s in registry():
        if not s.get("enabled") or s.get("mode") != "page_read":
            continue
        cad = str(s.get("cadence", ""))
        if cad == "every_run":
            ok = True
        elif cad.startswith("first_run:"):
            days = {_DAYS[d.strip()] for d in cad.split(":", 1)[1].split(",")}
            ok = first and now.weekday() in days
        else:
            ok = False
        (run if ok else skipped).append({"id": s["id"], "name": s["name"], "url": s.get("url"),
                                         "gap_s": max(MIN_GAP_S, s.get("crawl_delay_s") or 0)})
    return {"run": run, "skipped": [s["id"] for s in skipped],
            "rules": "page_read only; wait gap_s between reads; honest client identity; no login"}


# ---------------- paced reading (RT-13: a shell `sleep` is blocked in unattended runs) ----------------
def _last_read_at():
    from . import state
    rows = state._read("source-reads.jsonl")
    return datetime.fromisoformat(rows[-1].get("read_at") or rows[-1]["at"]) if rows else None


def read(source_id: str, url: str | None = None, now_fn=None, sleep_fn=None, reader=None) -> dict:
    """Read one enabled page_read source (or one page of it) with the pacing enforced HERE:
    waits until `gap_s` has passed since the previous read of any source. Saves the text and logs it."""
    import json as _json
    import subprocess
    import time
    from . import state
    from .util import now_iso, project_path
    now_fn = now_fn or (lambda: datetime.fromisoformat(now_iso()))
    sleep_fn = sleep_fn or time.sleep
    from .util import config
    if not config()["features"].get("web_discovery"):     # global switch, enforced in code (Hermes review 2026-11-17)
        return {"ok": False, "error": "features.web_discovery is false: no source is read"}
    src = next((s for s in registry() if s["id"] == source_id), None)
    if not src or not src.get("enabled") or src.get("mode") != "page_read":
        return {"ok": False, "error": f"{source_id} is not an enabled page_read source"}
    target = url or src["url"]
    from urllib.parse import urlparse
    allowed = {(urlparse(src["url"]).hostname or "").removeprefix("www.")} | set(src.get("detail_hosts") or [])
    if url and (urlparse(url).hostname or "").removeprefix("www.") not in allowed:
        return {"ok": False, "error": "url is outside this source's site (add it to detail_hosts only after a robots check)"}
    gap = max(MIN_GAP_S, src.get("crawl_delay_s") or 0)
    last = _last_read_at()
    waited = 0.0
    if last:
        waited = max(0.0, gap - (now_fn() - last).total_seconds())
        if waited:
            sleep_fn(waited)
    if reader is None:
        def reader(u):
            r = subprocess.run(["agent-reach", "web", "read", u], capture_output=True, text=True, timeout=120)
            return _json.loads(r.stdout or "{}")
    d = reader(target)
    text = " ".join(i.get("text") or "" for i in d.get("items", []))
    out = project_path("state") / "source-runs" / now_iso()[:10]
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{source_id}-{len(list(out.glob(source_id + '-*')))}.md"
    path.write_text(text, encoding="utf-8")
    rec = {"read_at": now_fn().isoformat(), "source": source_id, "url": target, "ok": bool(d.get("ok")) and len(text) > 200,
           "chars": len(text), "waited_s": round(waited, 1), "backend": d.get("backend"),
           "error": (d.get("error") or {}).get("code"), "file": str(path)}
    state._append("source-reads.jsonl", rec)
    return rec
