"""Deterministic listing sweep (RT-14b, 2026-11-16): no LLM, no tokens.

Reads the listing pages of the sources due in this run (paced by `sources.read`), parses one card per
job, and for each card: Seen check (stable identity) -> card triage (zone + title). Cards already seen
or clearly not aligned are logged here; only the short list of NEW, possibly aligned cards goes to the
Job Hunter, who reads those detail pages and classifies them. A source whose cards cannot be parsed is
returned as `needs_agent` so the Job Hunter reads it the old way (coverage never silently drops).
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from . import discovery, seen, sources, targets
from .util import now_iso, project_path

GENERIC_LINK_TEXT = re.compile(r"(?i)^(read more|find out more.*|apply.*|view.*|more info.*|details|learn more)$")
_LINK = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)")
_MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
_CLOSE_DMY = re.compile(r"(?i)clos\w*.{0,30}?\b(\d{1,2})\s+([a-z]{3})[a-z]*\.?,?\s+(\d{4})")
_CLOSE_MDY = re.compile(r"(?i)clos\w*.{0,30}?\b([a-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})")
_CLOSE_NUM = re.compile(r"(?i)clos\w*.{0,30}?\b(\d{1,2})/(\d{1,2})/(\d{4})")
_LOC_LABEL = re.compile(r"(?i)\blocation\s*:\s*([^:]{2,60}?)(?=\s+[A-Z][\w ]{2,20}:|$)")
MAX_PAGES = 8


def closing_date(text: str) -> str:
    for rx, order in ((_CLOSE_DMY, "dmy"), (_CLOSE_MDY, "mdy"), (_CLOSE_NUM, "num")):
        m = rx.search(text or "")
        if not m:
            continue
        try:
            if order == "dmy":
                d, mo, y = int(m.group(1)), _MONTHS[m.group(2).lower()[:3]], int(m.group(3))
            elif order == "mdy":
                mo, d, y = _MONTHS[m.group(1).lower()[:3]], int(m.group(2)), int(m.group(3))
            else:
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return f"{y:04d}-{mo:02d}-{d:02d}"
        except (KeyError, ValueError):
            continue
    return ""


_LOC_STOP = re.compile(r"(?i)\s+(applications?|permanent|full[ -]time|part[ -]time|casual|fixed[ -]term|contract|clos\w*)\b.*$")


def _location(lines: list[str]) -> tuple[str, dict]:
    loc, z = _location_raw(lines)
    return _LOC_STOP.sub("", loc).strip(" ,-"), z


def _location_raw(lines: list[str]) -> tuple[str, dict]:
    """First card segment that names a place (in or out of zone), else a region-only one."""
    region = None
    for l in lines:                      # an explicit "Location: ..." label wins
        m = _LOC_LABEL.search(l)
        if m:
            z = targets.zone_status(m.group(1))
            if z["status"] != "unknown":
                return m.group(1).strip(), z
    for l in lines:
        for seg in re.split(r"[·|•]|\s{2,}", re.sub(r"^[*\-\s]+", "", l)):
            seg = seg.strip()
            if not seg or len(seg) > 80:
                continue
            seg = re.sub(r"(?i)^location:?\s*", "", seg)
            z = targets.zone_status(seg)
            if z["status"] in ("in_zone", "out_of_zone"):
                return seg, z
            if z["status"] == "region_only" and region is None:
                region = (seg, z)
    if region:
        return region
    for l in lines:                      # last resort: a place named inside a long card line
        z = targets.zone_status(re.sub(r"^[*\-#\s]+", "", l))
        if z["status"] in ("in_zone", "out_of_zone"):
            return z.get("place", ""), z
    return "", {"status": "unknown"}


def _company(lines: list[str], default: str) -> str:
    """TSS cards carry the agency after the award line; other sources are one employer."""
    for i, l in enumerate(lines):
        if re.search(r"(?i)\b(award|agreement)\b", l) and i + 1 < len(lines):
            nxt = re.sub(r"^[*\-\s]+", "", lines[i + 1]).strip()
            if nxt and not nxt.startswith("$"):
                return nxt
    return default


def parse_cards(text: str, job_link: str, company: str) -> list[dict]:
    """One card per distinct job URL matching `job_link`. Title = the link text, or the nearest heading
    above it when the link says 'Find out more'. Card text = lines up to the next job link."""
    rx = re.compile(job_link)
    lines = text.splitlines()
    hits = []   # (line index, url, link text)
    for i, l in enumerate(lines):
        for m in _LINK.finditer(l):
            if rx.search(m.group(2)):
                hits.append((i, m.group(2).split(" ")[0], m.group(1).strip()))
    by_url: dict[str, dict] = {}
    order = []
    for n, (i, url, label) in enumerate(hits):
        nxt = next((j for j, u, _ in hits[n + 1:] if u != url), len(lines))
        good = label and not label.startswith("!") and not GENERIC_LINK_TEXT.match(label)
        if not good:
            hk = next((k for k in range(i - 1, max(-1, i - 12), -1) if lines[k].lstrip().startswith("#")), None)
            heading = re.sub(r"^#+\s*", "", lines[hk]).strip() if hk is not None else ""
            label = heading if heading and not _LINK.search(heading) else ""
            start = hk if hk is not None else i
        else:
            start = i
        if url not in by_url:
            order.append(url)
            by_url[url] = {"url": url, "title": label, "lines": lines[start:min(nxt, i + 16)]}
        elif not by_url[url]["title"] and label:
            by_url[url]["title"] = label
    cards = []
    for url in order:
        c = by_url[url]
        if not c["title"]:
            continue
        body = [l for l in c["lines"] if l.strip()]
        rest = [re.sub(_LINK, "", l) for l in body]
        loc, zone = _location(rest)
        card_text = "\n".join(body)
        cards.append({"url": url, "title": re.sub(r"\s+", " ", c["title"]).strip(), "location": loc, "zone": zone,
                      "closing": closing_date(card_text), "company": _company(rest, company), "card_text": card_text})
    return cards


def parse_heading_cards(text: str, level: int, base_url: str, company: str,
                        skip: str | None = None) -> list[dict]:
    """Sites that publish whole ads on one page under headings, without one link per job (P-12: Shaw).
    One card per heading of exactly `level` '#'; url = listing URL + '#<slug>' (stable identity)."""
    lines = text.splitlines()
    rx = re.compile(r"^#{%d}\s+(.+?)\s*$" % level)
    heads = [(i, rx.match(l).group(1)) for i, l in enumerate(lines) if rx.match(l)]
    cards = []
    for n, (i, title) in enumerate(heads):
        title = re.sub(r"[*_]", "", re.sub(_LINK, r"\1", title)).strip()
        if not title or (skip and re.search(skip, title)):
            continue
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        body = [l for l in lines[i:end] if l.strip()]
        rest = [re.sub(_LINK, "", l) for l in body]
        loc, zone = _location(rest)
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        card_text = "\n".join(body)
        cards.append({"url": f"{base_url.split('#')[0]}#{slug}", "title": title, "location": loc, "zone": zone,
                      "closing": closing_date(card_text), "company": _company(rest, company), "card_text": card_text})
    return cards


def _detail_allowed(url: str, cfg: dict) -> bool:
    if cfg.get("cards_by") == "heading" or cfg.get("detail") == "listing_only":
        return False                               # whole ad in the listing, or detail host disallows robots
    kind = discovery.classify_url(url)
    return not (kind and kind[0] in ("seek", "linkedin", "indeed"))   # employer job pages stay readable


def _total_pages(text: str) -> int | None:
    m = re.search(r"Displaying\s+\**\d+-(\d+)\**\s+of\s+\**(\d+)", text or "")
    if m:
        per, total = int(m.group(1)), int(m.group(2))
        return -(-total // max(per, 1))
    return None


def sweep(now: datetime, read=None, search=None, mail_messages=None) -> dict:
    """Run the deterministic part of a search. `read(source_id, url)` defaults to `sources.read`;
    `search(query, limit)` is the discovery search (P-12), run only when config discovery.enabled is true."""
    read = read or (lambda sid, url=None: sources.read(sid, url))
    reg = {s["id"]: s for s in sources.registry()}
    due = sources.due(now)
    shortlist, needs_agent, per_source = [], [], []
    for s in due["run"]:
        cfg = reg[s["id"]]
        stats = {"source": s["id"], "pages_read": 0, "cards": 0, "known_unchanged": 0, "logged_by_title": 0,
                 "out_of_zone": 0, "shortlisted": 0, "errors": []}
        pattern = cfg.get("job_link")
        page, pages_total, urls = 1, None, [cfg["url"]]
        while urls:
            url = urls.pop(0)
            rec = read(s["id"], None if url == cfg["url"] else url)
            stats["pages_read"] += 1
            if not rec.get("ok"):
                stats["errors"].append(rec.get("error") or "read failed")
                break
            text = Path(rec["file"]).read_text(encoding="utf-8")
            if not pattern and cfg.get("cards_by") != "heading":
                needs_agent.append({"source": s["id"], "file": rec["file"], "reason": "no card parser for this site"})
                break
            if cfg.get("cards_by") == "heading":
                cards = parse_heading_cards(text, int(cfg.get("heading_level", 4)), cfg["url"],
                                            cfg.get("employer") or cfg["name"], cfg.get("heading_skip"))
            else:
                cards = parse_cards(text, pattern, cfg.get("employer") or cfg["name"])
            for c in cards:
                if c["zone"]["status"] == "unknown" and cfg.get("default_location"):
                    c["location"], c["zone"] = cfg["default_location"], targets.zone_status(cfg["default_location"])
            if not cards:
                if re.search(r"(?i)no (current )?(vacanc|positions|jobs)|not currently (advertising|recruiting)", text):
                    stats["note"] = "employer says there are no vacancies"
                elif cfg.get("empty_ok") and len(text) > 2000:   # national board filtered to Tasmanian links (P-12)
                    stats["note"] = "no Tasmanian job on this page"
                else:
                    needs_agent.append({"source": s["id"], "file": rec["file"], "reason": "0 cards parsed"})
                break
            new_on_page = 0
            for c in cards:
                stats["cards"] += 1
                chk = seen.check(c["url"], c["card_text"], c["company"], c["title"], c["location"], c["closing"])
                if chk["status"] == "known_unchanged":
                    stats["known_unchanged"] += 1
                    continue
                new_on_page += 1
                tri = targets.triage(c["title"], c["location"], strict=cfg.get("title_filter") == "strict")
                if not tri["read_detail"]:
                    key = "out_of_zone" if tri["zone"]["status"] == "out_of_zone" else "logged_by_title"
                    stats[key] += 1
                    seen.add(c["url"], c["card_text"], "excluded", f"{tri['seen_destination_if_not_read']}; "
                             f"{tri['reason']} (sweep, card only)", c["company"], c["title"], c["location"],
                             rule="C1" if key == "out_of_zone" else "T0", closing=c["closing"])
                    continue
                stats["shortlisted"] += 1
                shortlist.append({"source": s["id"], **{k: c[k] for k in ("url", "title", "company", "location", "closing")},
                                  "zone": tri["zone"]["status"], "group": tri["group"],
                                  "catalogue_title": tri["catalogue_title"], "seen_status": chk["status"],
                                  "seen_previous": (chk.get("previous") or {}).get("dedup_key"),
                                  "why": tri["reason"],
                                  # P-12: ads that link to SEEK/LinkedIn/Indeed are never opened; the card is the evidence
                                  "read_detail_allowed": _detail_allowed(c["url"], cfg),
                                  "card_text": c["card_text"][:3000] if not _detail_allowed(c["url"], cfg) else None})
            tmpl = cfg.get("pages")
            pages_total = pages_total or _total_pages(text)
            # next page only while this page still had unseen cards (newest first) and pages remain
            if tmpl and new_on_page and page < min(pages_total or MAX_PAGES, MAX_PAGES):
                page += 1
                urls.append(tmpl.format(n=page))
        per_source.append(stats)
    disc = None
    from .util import config
    if (config().get("discovery") or {}).get("enabled") and due["run"]:
        disc = discovery.run(now, search=search)
        shortlist += disc.get("shortlist", [])
    # P-3 + P-12 D-P12-1: job-alert e-mails (read-only IMAP, card text only, links never opened), every run
    mail = None
    if config()["features"].get("email_alerts"):
        from . import mailalerts
        mail = mailalerts.run(now, messages=mail_messages, commit=False)   # mark read only after the sweep file exists
        shortlist += mail.get("shortlist", [])
    out = {"at": now_iso(), "simulated_now": now.isoformat(), "per_source": per_source, "shortlist": shortlist,
           "discovery": {k: disc[k] for k in ("per_source",) if disc} if disc else None,
           "mail_alerts": {k: v for k, v in mail.items() if k not in ("shortlist", "new_state")} if mail else None,
           "needs_agent": needs_agent, "skipped_sources": due.get("skipped", []),
           "next": "Job Hunter: read ONLY the shortlist detail pages (bin/hcb sources read --id --url), "
                   "then targets match / classify / seen add; read needs_agent sources the old way."}
    d = project_path("state") / "sweeps"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"sweep-{now:%Y%m%d-%H%M}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if mail and mail.get("new_state"):
        from . import mailalerts
        mailalerts.commit(mail["new_state"])
    return out
