"""Seen-Postings Log (job-hunter.md JH-T11), persisted in state/seen.jsonl.

Every posting the Job Hunter has decided on gets one entry, whatever its destination (Baserow or
excluded). Before A-H (the expensive step) the Job Hunter asks `check()`:
- new             -> process normally;
- known_unchanged -> skip: no A-H, no digest line, no contact research (saves tokens, no repeats);
- known_changed   -> the closing date changed (re-posted / extended): re-evaluate and update the record.
Keys: the portal job id when there is one (SEEK 95841056 is the same job on any URL), else the
canonical URL, plus a company+title+location key to catch the same job on two sites
(possible duplicate -> the Job Hunter decides, then Baserow dedup still runs before any write).
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from . import state
from .util import fold, now_iso, sha256_bytes

_JOB_ID = [
    ("seek", re.compile(r"seek\.com(?:\.au)?/job/(\d+)")),
    ("linkedin", re.compile(r"linkedin\.com/jobs/view/(?:[^/?]*-)?(\d+)")),
    ("indeed", re.compile(r"[?&]jk=([0-9a-f]+)")),
]


_ID_PARAMS = re.compile(r"(?i)^(id|jobid|job_id|job|vacancyid|vacancy|reqid|requisitionid|pid|ref)$")


def canonical_url(url: str) -> str:
    """host+path, plus the fragment and job-id query params when present: several employer pages list
    every job on ONE path and tell them apart by '#job-12' or '?id=12' (RT-13: Huon 12 ads -> 1 key)."""
    u = urlparse((url or "").strip())
    host = (u.hostname or "").lower().removeprefix("www.")
    base = f"{host}{u.path.rstrip('/')}".lower()
    ids = sorted(p for p in (u.query or "").split("&") if "=" in p and _ID_PARAMS.match(p.split("=", 1)[0]))
    if ids:
        base += "?" + "&".join(ids).lower()
    if u.fragment:
        base += "#" + u.fragment.lower()
    return base


def dedup_key(url: str) -> str:
    for site, rx in _JOB_ID:
        m = rx.search(url or "")
        if m:
            return f"{site}:{m.group(1)}"
    return "url:" + canonical_url(url)


def content_hash(ad_text: str) -> str:
    norm = re.sub(r"\s+", " ", fold(ad_text or "")).strip()
    return sha256_bytes(norm.encode("utf-8"))[:16]


def job_key(company: str, title: str, location: str) -> str:
    return "|".join(re.sub(r"[^a-z0-9]+", " ", fold(x or "")).strip() for x in (company, title, location))


def _entries() -> list[dict]:
    return state._read("seen.jsonl")


def _host(key_or_url: str) -> str:
    u = key_or_url.split(":", 1)[1] if key_or_url.startswith("url:") else key_or_url
    return u.split("/", 1)[0]


def _unique_key(key: str) -> bool:
    """A key that names ONE job (portal id, or a URL carrying a job number / #fragment), unlike a shared
    listing URL: same key = same job whatever company string the agent wrote (RT-14b: 'Department of
    Health' vs 'Tasmanian State Service')."""
    return not key.startswith("url:") or "#" in key or bool(re.search(r"\d{3,}", key))


def _same_job(e: dict, jk: str) -> bool:
    return bool(jk.strip("|")) and e.get("job_key") == jk


def check(url: str, ad_text: str, company: str = "", title: str = "", location: str = "",
          closing: str = "") -> dict:
    """Status is decided by the stable card identity (company+title+location, plus the closing date when
    both sides have one), NOT by the text the agent happened to pass (RT-14: the full ad in one run and the
    listing card in the next gave 0 known_unchanged out of 65). content_hash is only a fallback when a
    side has no job identity."""
    key, h, jk = dedup_key(url), content_hash(ad_text), job_key(company, title, location)
    entries = _entries()
    last = None
    for e in entries:
        if e["dedup_key"] != key:
            continue
        if _same_job(e, jk) or _unique_key(key) or not e.get("job_key", "").strip("|") or not jk.strip("|"):
            last = e
    if last:
        if _same_job(last, jk) or (_unique_key(key) and jk.strip("|")):
            prev_c = last.get("closing") or ""
            changed = bool(closing and prev_c and closing != prev_c)
            status = "known_changed" if changed else "known_unchanged"
            why = "closing date changed" if changed else "same job identity"
        else:
            status = "known_unchanged" if last["content_hash"] == h else "known_changed"
            why = "no job identity on one side: compared text hash"
        return {"status": status, "basis": why, "dedup_key": key, "content_hash": h, "previous": last}
    same_job = [e for e in entries if _same_job(e, jk)]
    same_site = [e for e in same_job if _host(e["dedup_key"]) == _host(key) or
                 _host(e.get("canonical_url", "")) == _host(canonical_url(url))]
    if same_site:
        return {"status": "known_unchanged", "basis": "same job on the same site, URL format changed",
                "dedup_key": key, "content_hash": h, "previous": same_site[-1]}
    if same_job:
        return {"status": "possible_duplicate", "dedup_key": key, "content_hash": h, "matches": same_job[-3:],
                "note": "same company+title+location from another source: decide if it is the same vacancy"}
    return {"status": "new", "dedup_key": key, "content_hash": h}


def add(url: str, ad_text: str, destination: str, reason: str, company: str = "", title: str = "",
        location: str = "", baserow_id=None, rule: str | None = None, closing: str = "") -> dict:
    rec = {"dedup_key": dedup_key(url), "canonical_url": canonical_url(url), "content_hash": content_hash(ad_text),
           "job_key": job_key(company, title, location), "destination": destination, "reason": reason,
           "baserow_id": baserow_id, "rule": rule, "closing": closing or None, "decided_at": now_iso()}
    return state._append("seen.jsonl", rec)
