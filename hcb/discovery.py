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
    # P-15 (2026-11-28) aggregators and agency sites seen in the Rio Tinto case: hints only, never opened
    ("jora", r"jora\.com/(?:job|view-job)/", False),
    ("viewjobs", r"viewjobs\.com\.au/listing/", False),
    ("regionaljobs", r"movetomore\.com\.au/job/", False),
    ("resourcejobs", r"resourcejobs\.au/jobs/", False),
    ("jobstralia", r"jobstralia\.com/detail/", False),
    ("jobau", r"jobau\.org/[^/]+/\d{4}-\d{2}-", False),
    ("jooble", r"jooble\.org/jdp/\d+", False),
    ("zammejobs", r"zammejobs\.com/jobs/", False),
    ("workinaus", r"workinaus\.com\.au/jobs?/\d", False),
    ("chandlermacleod", r"chandlermacleod\.com/job-details/", False),
]
PORTAL_LISTING = re.compile(r"(?i)https?://(?:[a-z]+\.)?(?:seek\.com(?:\.au)?|jora\.com|indeed\.com(?:\.au)?)/(?!job/|viewjob)")
MAX_QUERIES_PER_RUN = 4


def _cfg() -> dict:
    return util.config().get("discovery") or {}


def due_sources() -> list[dict]:
    """Enabled search_discovery sources and the P-15 employer + agency queries, least recently searched first."""
    last = {}
    for r in state._read("discovery-runs.jsonl"):
        last[r.get("source")] = r.get("at", "")
    regs = [s for s in sources.registry() if s.get("enabled") and s.get("mode") == "search_discovery"]
    regs += agency_sources()
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


_NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
        "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40}
_UNIT_DAYS = {"m": 0, "min": 0, "minute": 0, "h": 0, "hour": 0, "d": 1, "day": 1, "w": 7, "week": 7, "month": 30}
_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _num(word: str) -> int | None:
    w = word.lower()
    if w.isdigit():
        return int(w)
    parts = [p for p in re.split(r"[\s-]+", w) if p]
    if parts and all(p in _NUM for p in parts):
        return sum(_NUM[p] for p in parts)
    return None


def card_date(item: dict, now: datetime) -> str | None:
    """P-15: the date a result shows, as YYYY-MM-DD: `published_at`, else 'Date posted: November 27, 2026',
    '13-Nov-2026', 'Listed nine hours ago', 'Posted 7h ago', 'Listed 2 weeks ago' in date_shown or the text."""
    from datetime import timedelta
    pub = item.get("published_at") or item.get("published")
    if pub and str(pub) not in ("None", "N/A"):
        try:
            return datetime.fromisoformat(str(pub).replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            pass
    for text in (item.get("date_shown"), (item.get("text") or item.get("snippet") or "")[:1500]):
        t = str(text or "")
        m = re.search(r"(?i)\b(\d{1,2})[-\s]([a-z]{3})[a-z]*[-\s,]+(20\d\d)\b", t)
        if m and m.group(2).lower() in _MONTHS:
            return f"{m.group(3)}-{_MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
        m = re.search(r"(?i)\b([a-z]{3})[a-z]*\s+(\d{1,2}),?\s+(20\d\d)\b", t)
        if m and m.group(1).lower() in _MONTHS:
            return f"{m.group(3)}-{_MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
        m = re.search(r"(?i)(?:\b([a-z]+)[\s-])?\b(\d+|[a-z]+)\s*(m|min|minute|h|hour|d|day|w|week|month)s?\s+ago\b", t)
        if m:
            n = _num(f"{m.group(1)} {m.group(2)}") if m.group(1) else None   # "twenty three days ago"
            n = n if n is not None else _num(m.group(2))
            if n is not None:
                return (now - timedelta(days=n * _UNIT_DAYS[m.group(3).lower()])).date().isoformat()
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
    elif d.tzinfo is not None and now.tzinfo is None:
        d = d.replace(tzinfo=None)
    return (now - d).days > MAX_AGE_DAYS


def agency_sources() -> list[dict]:
    """P-15 D-P15-3: contract roles a recruitment agency posts for a target employer (Chandler Macleod is Rio Tinto's
    contract provider) never appear on the employer's careers page. One rotating query per employer + agency."""
    out = []
    for e in util.load_yaml(util.ROOT / "config" / "employers.yaml").get("employers", []):
        for a in e.get("agencies") or []:
            out.append({"id": f"AGENCY-{e['id']}-{re.sub(r'[^a-z0-9]+', '', a['name'].lower())}", "name": a["name"],
                        "employer": a["name"], "client": e["name"], "mode": "search_discovery", "enabled": True,
                        "query": a.get("query") or f'"{a["name"]}" "{e["name"]}" job', "title_filter": "loose"})
    return out


_LINKEDIN_HIRING = re.compile(r"^(?P<co>.+?) hiring (?P<title>.+?) in (?P<place>[^|]+?)(?:\s*\|\s*LinkedIn)?$")


def clean_title(title: str) -> str:
    """'Business Analyst Specialist | Regional Jobs', '... — Chandler Macleod | ViewJobs', '... at Chandler Macleod',
    'JLE Group hiring Project Engineer in Launceston, ... | LinkedIn', '... job in Mining Resources & Energy in Bell Bay'."""
    t = re.sub(r"\s+", " ", title or "").strip()
    m = _LINKEDIN_HIRING.match(t)
    if m:
        return m.group("title").strip()[:140]
    t = re.sub(r"(?i)\s+job in\s+.+$", "", t)
    t = re.sub(r"(?i)^(?:jobs?\s*-\s*)?(?:job details\s*-\s*)", "", t)
    t = re.split(r"\s+[|\-–]\s+(?:SEEK|LinkedIn|Indeed|Careers|Jobs|Built In)\b", t)[0]
    t = re.sub(r"\s+\|\s+[^|]{2,40}$", "", t)                 # trailing "| Site"
    t = re.split(r"\s+[—–]\s+", t)[0]                         # "Title — Company"
    t = re.sub(r"(?i)\s+at\s+[A-Z][\w&' .-]{2,60}$", "", t)    # "Title at Company"
    return t.strip()[:140]


def _company_from(title: str) -> str:
    """Only when the result says it plainly ('X hiring', 'at X', '— X | Site'); never a place, never a guess."""
    t = re.sub(r"\s+", " ", title or "").strip()
    m = _LINKEDIN_HIRING.match(t)
    if m:
        return m.group("co").strip()
    m = re.search(r"(?i)\sat\s+([A-Z][\w&' .-]{2,60}?)(?:\s+[—–|]|$)", t) or \
        re.search(r"\s[—–]\s+([^|—–]+?)\s+\|", t)
    if not m:
        return ""
    co = m.group(1).strip()
    return "" if _place(co, "") else co


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
    in_run: set = set()                      # one ad syndicated to two aggregators in the same results = one card
    run_keys: list = []
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
            date = card_date(it, now)
            if _too_old(date, now):
                stats["too_old"] += 1
                continue
            stats["job_urls"] += 1
            title = clean_title(it.get("title") or "")
            snippet = (it.get("text") or it.get("snippet") or "")[:1500]
            loc = _place(title, snippet)
            if GENERIC_TITLE.search(title) or not title:
                continue                                  # a listing or search page, not one job
            company = src.get("employer") or src["name"]
            jk, dk = seen.job_key(company, title, loc), seen.dedup_key(url)
            if dk in in_run or _in_run(jk, run_keys):
                stats["known_unchanged"] += 1
                continue
            in_run.add(dk)
            run_keys.append(jk)
            chk = seen.check(url, snippet, company, title, loc, "")
            if chk["status"] == "known_unchanged" or _recent_duplicate(chk, now):
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
                              "why": tri["reason"], "date": date or "unknown",
                              **({"client": src["client"]} if src.get("client") else {}),
                              "note": None if kind[1] else (f"{kind[0]}: do not open the page; find the employer's own ad, "
                                                            "else the user opens the link")})
        state._append("discovery-runs.jsonl", {"at": now_iso(), "source": src["id"], "query": q,
                                                "results": stats["results"], "job_urls": stats["job_urls"],
                                                "shortlisted": stats["shortlisted"], "error": stats["error"]})
        per_source.append(stats)
    return {"ok": True, "simulated_now": now.isoformat(), "per_source": per_source, "shortlist": shortlist}


# ---------------- P-15 native search alarm (OpenAI web search, inside a Job Hunter turn) ----------------

def native_queries(now: datetime) -> dict:
    """The 2 fixed searches of the day for the Job Hunter's native web_search (rotating by day). After
    `discovery.native.trial_until` it returns none: the user decides whether the trial continues (D-P15-2)."""
    cfg = _cfg().get("native") or {}
    if not cfg.get("enabled"):
        return {"queries": [], "note": "discovery.native.enabled is false"}
    until = str(cfg.get("trial_until") or "")
    if until and now.date().isoformat() > until:
        return {"queries": [], "note": f"native-search trial ended {until}: ask the user whether to keep it"}
    pool = [f"{t} job Tasmania" for t in targets.queries()[:12]] + [s["query"] for s in agency_sources()]
    n = int(cfg.get("per_day", 2))
    start = (now.toordinal() * n) % max(len(pool), 1)
    return {"queries": [pool[(start + i) % len(pool)] for i in range(min(n, len(pool)))],
            "trial_until": until or None}


def _verbatim(phrase: str, *texts: str) -> bool:
    f = lambda x: re.sub(r"\s+", " ", util.fold(x or ""))
    return bool(phrase) and any(f(phrase) in f(t) for t in texts)


def ingest(results: dict, now: datetime) -> dict:
    """`bin/hcb discovery ingest`: results of the Job Hunter's native searches -> cards, by code. A job-ad URL is a
    card like Exa's; a SEEK / Jora / Indeed listing page is an ALARM card only when the Job Hunter quoted a
    role_title and a place that appear word for word in the result (no invented titles). Nothing is opened."""
    stats = {"results": 0, "job_ads": 0, "alarms": 0, "known": 0, "too_old": 0, "out_of_zone": 0,
             "logged_by_title": 0, "unverified_titles": 0, "skipped": 0}
    shortlist, in_run, run_keys = [], set(), []
    for srch in results.get("searches") or []:
        for r in srch.get("results") or []:
            stats["results"] += 1
            url = (r.get("url") or "").split("#")[0]
            title_raw, snippet = r.get("title") or "", (r.get("snippet") or "")[:600]
            date = card_date({"date_shown": r.get("date_shown"), "text": snippet}, now)
            if _too_old(date, now):
                stats["too_old"] += 1
                continue
            kind = classify_url(url)
            alarm = False
            if kind and not GENERIC_TITLE.search(clean_title(title_raw)):
                title, company = clean_title(title_raw), _company_from(title_raw)
                loc = _place(title_raw, snippet)
                stats["job_ads"] += 1
            elif PORTAL_LISTING.match(url) and r.get("role_title"):
                title, loc = str(r["role_title"]).strip(), str(r.get("place") or "").strip()
                if not (_verbatim(title, snippet, title_raw) and _verbatim(loc, snippet, title_raw)):
                    stats["unverified_titles"] += 1
                    continue
                company, alarm, kind = "", True, ("portal_listing", False)
                stats["alarms"] += 1
            else:
                stats["skipped"] += 1
                continue
            jk, dk = seen.job_key(company, title, loc), seen.dedup_key(url)
            if dk in in_run or _in_run(jk, run_keys):
                stats["known"] += 1
                continue
            in_run.add(dk)
            run_keys.append(jk)
            chk = seen.check(url, snippet, company, title, loc, "")
            if chk["status"] == "known_unchanged" or _recent_duplicate(chk, now) or \
                    (alarm and _known_by_title_place(title, loc)):
                stats["known"] += 1
                continue
            if loc in _out_places() or not loc or _foreign(title_raw, snippet, url):
                stats["out_of_zone"] += 1
                continue
            tri = targets.triage(title, loc)
            if not tri["read_detail"]:
                stats["logged_by_title"] += 1
                continue
            shortlist.append({"source": "NATIVE", "channel": "native_search", "platform": kind[0],
                              "read_detail_allowed": False, "url": url, "title": title, "company": company,
                              "location": loc, "closing": "", "zone": tri["zone"]["status"], "group": tri["group"],
                              "catalogue_title": tri["catalogue_title"], "seen_status": chk["status"],
                              "why": tri["reason"], "date": date or "unknown", "query": srch.get("query"),
                              "review_reason": "aviso en portal: falta el aviso completo",
                              "note": ("alarma: el aviso aparece en una página de listados del portal; no abrirla. "
                                       "Buscar el aviso del empleador o de un agregador, si no el usuario envía el aviso")
                                      if alarm else f"{kind[0]}: do not open the page; the user opens the link"})
    state._append("discovery-runs.jsonl", {"at": now_iso(), "source": "NATIVE",
                                            "query": " || ".join(s.get("query", "") for s in results.get("searches") or []),
                                            "results": stats["results"], "job_urls": stats["job_ads"],
                                            "alarms": stats["alarms"], "shortlisted": len(shortlist), "error": None})
    return {"ok": True, "stats": stats, "shortlist": shortlist,
            "next": "Job Hunter: treat these like other read_detail_allowed:false cards (targets match / classify / "
                    "seen add, review_reason as given). Never open SEEK, LinkedIn, Indeed or Jora pages."}


US_PLACE = re.compile(r"(?:,\s*[A-Z]{2}\s+\d{5}\b|\bindeed\.com\b(?!\.au)|,\s*(?:NY|OH|CA|TX|PA|NJ|IN|WI)\b)")


def _foreign(title: str, snippet: str, url: str) -> bool:
    """'CPQ Analyst - Troy, OH 45374 - Indeed.com' named Hobart (Hobart Service): a US result, not Tasmania."""
    return bool(US_PLACE.search(title or "") or re.search(r"https?://(?:www\.)?indeed\.com/", url or ""))


def _recent_duplicate(chk: dict, now: datetime) -> bool:
    """Same company + title + place already seen from another source within MAX_AGE_DAYS = the same ad
    (P-15: Baserow row 39 and its aggregator copies). An older match may be a new posting: kept for review."""
    if chk.get("status") != "possible_duplicate":
        return False
    for m in chk.get("matches") or []:
        if not _too_old((m.get("decided_at") or m.get("at") or "")[:10] or None, now):
            return True
    return False


def _in_run(jk: str, keys: list) -> bool:
    return any(seen._same_job({"job_key": k}, jk) for k in keys)


def _known_by_title_place(title: str, loc: str) -> bool:
    jk = seen.job_key("", title, loc)
    return any(seen._same_job(e, jk) for e in state._read("seen.jsonl"))
