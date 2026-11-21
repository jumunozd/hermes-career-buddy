"""Search discovery (P-12 D-P12-4): a safety net for employers whose listings cannot be read directly.

No LLM. For the `search_discovery` sources that are enabled, a few web searches per run (rotating, least
recently searched first) look for job ads of that employer in Tasmania. Search results are DATA: only result
URLs that match a known job-ad pattern become cards; nothing in a result is followed or obeyed. Pages of
portals whose terms forbid automated reading (SEEK, LinkedIn, Indeed) are never opened: the search snippet
is the card and the user opens the link. Cards then go through the same Seen check and triage as the sweep.
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime

from . import seen, sources, state, targets
from . import util
from .util import now_iso

# job-ad URL patterns per platform; a result is a card only if its URL matches one of these
JOB_URL = [
    ("seek", r"(?:seek\.com\.au|au\.seek\.com)/job/\d+", False),
    ("linkedin", r"linkedin\.com/jobs/view/[\w-]*\d+", False),
    ("indeed", r"indeed\.com(?:\.au)?/.*[?&]jk=[0-9a-f]{16}", False),
    ("workday", r"myworkdayjobs\.com/.+/job/", True),
    ("pageup", r"pageuppeople\.com/.+/(?:job|en/job)/\d+", True),
    ("livehire", r"livehire\.com/.+/job/", True),
    ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/[^/]+/\d+", True),
    ("oracle", r"oraclecloud\.com/hcmUI/CandidateExperience/.+/job/\d+", True),
    ("dayforce", r"dayforcehcm\.com/.+/jobs/\d+", True),
    ("elmo", r"elmotalent\.com\.au/careers/.+/job/view/\d+", True),
    ("applynow", r"applynow\.net\.au/jobs/", True),
    ("employmenthero", r"employmenthero\.com/jobs/(?:position|job)/", True),
    ("work180", r"work180\.com/.+/job/\d+", True),
    ("tss", r"careers\.jobs\.tas\.gov\.au/(?:en/)?jobs?/\d+", True),
]
MAX_QUERIES_PER_RUN = 4


def _cfg() -> dict:
    return util.config().get("discovery") or {}


def due_sources() -> list[dict]:
    """Enabled search_discovery sources, least recently searched first."""
    last = {}
    for r in state._read("discovery-runs.jsonl"):
        last[r.get("source")] = r.get("at", "")
    regs = [s for s in sources.registry() if s.get("enabled") and s.get("mode") == "search_discovery"]
    return sorted(regs, key=lambda s: last.get(s["id"], ""))


def query_for(src: dict) -> str:
    return src.get("query") or f'"{src.get("employer") or src["name"]}" job Tasmania'


# job boards and aggregators: a hint only (never canonical, never opened); the canonical ad is the employer's
AGGREGATOR_PATH = re.compile(r"(?i)https?://[^/]+/(?:[a-z-]+/)*(?:job|jobs|jobdetail|job-detail|vacanc\w*|position)s?(?:/|-|\?)")
MAX_AGE_DAYS = 45
GENERIC_TITLE = re.compile(r"(?i)^(?:[\w&' ]+ )?(?:vacancies|careers|jobs|current opportunities|job search)\b|\bjobs in\b|\d+ jobs\b")
OUT_OF_ZONE_PLACES = ["King Island", "Flinders Island", "Smithton", "Circular Head", "Stanley", "Zeehan", "Tullah",
                      "Waratah", "Poatina", "Tarraleah", "Bothwell", "Ouse", "Triabunna", "Swansea", "Bicheno", "Orford",
                      "Cygnet", "Geeveston", "Victoria", "Melbourne", "Sydney", "Brisbane", "Adelaide", "Perth", "Darwin",
                      "Canberra", "NSW", "QLD", "VIC"]


def _out_places() -> list[str]:
    zones = util.load_yaml(util.ROOT / "config" / "sources.yaml")["zones"]
    return list(zones.get("out_of_scope_examples") or []) + OUT_OF_ZONE_PLACES


def _place(title: str, snippet: str) -> str:
    """The most specific place named in the title, then in the snippet: out-of-zone places win over 'Tasmania'."""
    out = _out_places()
    inz = ["Hobart", "Launceston", "Devonport", "Burnie", "Glenorchy", "Clarence", "Kingborough", "Bell Bay",
           "George Town", "Boyer", "New Norfolk", "Wynyard", "Ulverstone", "Latrobe", "Brighton", "Cambridge",
           "Claremont", "Lutana", "Derwent Park", "Penguin", "Heybridge", "Spreyton", "Railton"]
    for text in (title, snippet[:400]):
        for p in out + inz:
            if re.search(r"(?i)\b" + re.escape(p) + r"\b", text):
                return p
    return "Tasmania" if re.search(r"(?i)\btasmania|\btas\b", title + " " + snippet[:400]) else ""


def classify_url(url: str) -> tuple[str, bool] | None:
    for name, rx, readable in JOB_URL:
        if re.search(rx, url):
            return name, readable
    if AGGREGATOR_PATH.match(url):
        return "aggregator", False
    return None


def _too_old(published: str | None, now: datetime) -> bool:
    if not published:
        return False
    try:
        d = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
    except ValueError:
        return False
    if d.tzinfo is None and now.tzinfo is not None:
        d = d.replace(tzinfo=now.tzinfo)
    return (now - d).days > MAX_AGE_DAYS


def _default_search(q: str, limit: int) -> dict:
    import sys
    if "unittest" in sys.modules:   # tests never reach the web (same guard as Telegram and Baserow)
        return {"ok": False, "error": {"code": "REFUSED_UNDER_TEST"}, "items": []}
    r = subprocess.run(["agent-reach", "web", "search", q, "--limit", str(limit)], capture_output=True, text=True, timeout=120)
    return json.loads(r.stdout or "{}")


def run(now: datetime, search=None, max_queries: int | None = None) -> dict:
    if not util.config()["features"].get("web_discovery"):
        return {"ok": False, "error": "features.web_discovery is false", "shortlist": [], "per_source": []}
    if now.hour < sources.FIRST_RUN_BEFORE_HOUR and not _cfg().get("first_run_too"):
        # the 07:30 run already reads the weekly listings; searches go to the lighter 12:30 / 16:30 runs (180 s limit)
        return {"ok": True, "skipped": "first run of the day: discovery runs at 12:30 and 16:30", "shortlist": [],
                "per_source": []}
    search = search or _default_search
    max_queries = max_queries or _cfg().get("max_queries_per_run", MAX_QUERIES_PER_RUN)
    limit = _cfg().get("results_per_query", 10)
    shortlist, per_source = [], []
    for src in due_sources()[:max_queries]:
        q = query_for(src)
        stats = {"source": src["id"], "query": q, "results": 0, "job_urls": 0, "too_old": 0, "known_unchanged": 0,
                 "logged_by_title": 0, "out_of_zone": 0, "shortlisted": 0, "error": None}
        d = search(q, limit)
        if not d.get("ok"):
            stats["error"] = (d.get("error") or {}).get("code") or "search failed"
        for it in d.get("items") or []:
            stats["results"] += 1
            url = (it.get("url") or "").split("#")[0]
            kind = classify_url(url)
            if not kind:
                continue
            if _too_old(it.get("published_at"), now):
                stats["too_old"] += 1
                continue
            stats["job_urls"] += 1
            title = re.sub(r"\s+", " ", it.get("title") or "").strip()
            title = re.sub(r"(?i)^(?:jobs?\s*-\s*)?(?:job details\s*-\s*)", "", title)
            title = re.split(r"\s+[|\-–]\s+(?:SEEK|LinkedIn|Indeed|Careers|Jobs|Built In)\b", title)[0][:140]
            snippet = (it.get("text") or it.get("snippet") or "")[:1500]
            loc = _place(title, snippet)
            if GENERIC_TITLE.search(title) or not title:
                continue                                  # a listing or search page, not one job
            company = src.get("employer") or src["name"]
            chk = seen.check(url, snippet, company, title, loc, "")
            if chk["status"] == "known_unchanged":
                stats["known_unchanged"] += 1
                continue
            if loc in _out_places():
                stats["out_of_zone"] += 1
                seen.add(url, snippet, "excluded", f"out of zone: {loc} (discovery, search result only)",
                         company, title, loc, rule="C1")
                continue
            tri = targets.triage(title, loc, strict=src.get("title_filter", "strict") == "strict")
            if not tri["read_detail"]:
                key = "out_of_zone" if tri["zone"]["status"] == "out_of_zone" else "logged_by_title"
                stats[key] += 1
                seen.add(url, snippet, "excluded", f"{tri['seen_destination_if_not_read']}; {tri['reason']} "
                         "(discovery, search result only)", company, title, loc,
                         rule="C1" if key == "out_of_zone" else "T0")
                continue
            stats["shortlisted"] += 1
            shortlist.append({"source": src["id"], "channel": "search_discovery", "platform": kind[0],
                              "read_detail_allowed": kind[1], "url": url, "title": title, "company": company,
                              "location": loc, "closing": "", "zone": tri["zone"]["status"], "group": tri["group"],
                              "catalogue_title": tri["catalogue_title"], "seen_status": chk["status"],
                              "why": tri["reason"],
                              "note": None if kind[1] else (f"{kind[0]}: do not open the page; find the employer's own ad, "
                                                            "else the user opens the link")})
        state._append("discovery-runs.jsonl", {"at": now_iso(), "source": src["id"], "query": q,
                                                "results": stats["results"], "job_urls": stats["job_urls"],
                                                "shortlisted": stats["shortlisted"], "error": stats["error"]})
        per_source.append(stats)
    return {"ok": True, "simulated_now": now.isoformat(), "per_source": per_source, "shortlist": shortlist}
