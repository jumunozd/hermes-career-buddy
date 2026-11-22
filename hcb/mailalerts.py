"""Job-alert e-mails as a source (P-3 + P-12 D-P12-1). No LLM, read-only, never opens a link.

The user's portals (SEEK, LinkedIn, employer platforms) send alerts to a dedicated iCloud alias; a mail rule
moves them to one folder. This module:
- opens that folder with IMAP EXAMINE (read-only: no flag, move or delete code exists) and fetches only
  messages newer than the last processed UID (`state/mail-alerts-state.json`);
- parses ONLY messages whose From domain is in config/email-alerts.yaml; others are counted by domain;
- turns each alert card into title / company / location / link, then runs the same seen + triage as the
  listing sweep. The card text is the evidence: SEEK/LinkedIn/Indeed pages are never read, and alert links
  (tracking redirects) are never opened by the system; they are kept for the user to click.
"""
from __future__ import annotations

import email
import imaplib
import json
import re
import sys
from email import policy
from email.utils import parseaddr
from pathlib import Path

from . import seen, state, targets
from .util import ROOT, config, load_yaml, now_iso, project_path

IMAP_HOST, IMAP_PORT = "imap.mail.me.com", 993
MAX_MESSAGES_PER_RUN = 40
STATE_FILE = "mail-alerts-state.json"
URL = re.compile(r"<?(https://[^\s<>]+)>?")


def alerts_config() -> dict:
    return load_yaml(ROOT / "config" / "email-alerts.yaml")


def sender_id(from_header: str, cfg: dict | None = None) -> str | None:
    addr = parseaddr(from_header or "")[1].lower()
    dom = addr.rsplit("@", 1)[-1] if "@" in addr else ""
    for s in (cfg or alerts_config()).get("senders", []):
        if any(dom == d or dom.endswith("." + d) for d in s.get("domains", [])):
            return s["id"]
    return None


# ---------- parsers (one per sender; each returns cards) ----------

def _plain(msg) -> str:
    part = msg.get_body(("plain",))
    if part is not None:
        return part.get_content()
    html = msg.get_body(("html",))
    if html is None:
        return ""
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", html.get_content())
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|td|h\d|li)>", "\n", t)
    t = re.sub(r"(?i)<a [^>]*href=\"(https://[^\"]+)\"[^>]*>", r" <\1> ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    import html as _h
    return _h.unescape(t)


NOISE = re.compile(r"(?i)^(recently posted|new|featured|be an early applicant|quick apply|view (more )?jobs?.*|"
                   r"\$[\d,]+.*|[\d,.]+\s*(k|per (hour|year|annum)).*|see all.*)$")


def parse_seek(text: str) -> list[dict]:
    """SEEK alert / recommendation e-mails (plain part): each card starts after a '[image: logo]' line with
    title, company and location lines, optional salary and bullet lines, then the job link."""
    cards = []
    blocks = re.split(r"(?m)^\s*\[image: [^\]]*logo[^\]]*\]\s*$", text)[1:]
    for b in blocks:
        lines = [l.strip() for l in b.strip().splitlines()]
        url = next((m.group(1) for l in lines for m in [URL.fullmatch(l)] if m), None)
        head = [l for l in lines if l and not URL.fullmatch(l) and not l.startswith(("-", "•", "*", "[image"))]
        if len(head) < 3 or not url:
            continue
        title, company, location = head[0], head[1], head[2]
        if NOISE.match(title) or len(title) > 120:
            continue
        cut = b.find("<" + url) if ("<" + url) in b else b.find(url)
        card_text = re.sub(r"<https://[^>]+>", "", b[:cut if cut > 0 else None]).strip()
        salary = next((l for l in head[3:6] if re.match(r"^\$[\d,]", l)), "")
        cards.append({"title": title, "company": company, "location": location, "url": url,
                      "salary": salary, "card_text": card_text[:2000]})
    return cards


PARSERS = {"seek": parse_seek}


def _one_time_forward(msg, cfg) -> str | None:
    """A single, dated test allowance kept in private/config (the user, 2026-11-22): a forward from the user's
    own address is read only if the forwarded original sender is allowlisted and the date has not passed."""
    from datetime import date
    from . import mailer
    ot = (mailer.mailbox() or {}).get("one_time_forward") or {}
    frm = parseaddr(msg.get("From", ""))[1].lower()
    try:
        until = date.fromisoformat(str(ot.get("until")))
    except ValueError:
        return None
    if not ot.get("from") or frm != str(ot["from"]).lower() or date.today() > until:
        return None
    m = re.search(r"(?im)^(?:from|de):\s*(.+@[^\s>]+>?)\s*$", _plain(msg)[:3000])
    return sender_id(m.group(1), cfg) if m else None


def parse_message(raw: bytes, cfg: dict | None = None) -> dict:
    msg = email.message_from_bytes(raw, policy=policy.default)
    sid = sender_id(msg.get("From", ""), cfg)
    out = {"from_domain": parseaddr(msg.get("From", ""))[1].rsplit("@", 1)[-1].lower(),
           "subject": str(msg.get("Subject", ""))[:200], "date": str(msg.get("Date", "")), "sender": sid, "cards": []}
    if not sid:
        sid = _one_time_forward(msg, cfg)
        out["sender"] = sid
        if sid:
            out["via"] = "one_time_forward_test"
    if not sid:
        out["skipped"] = "sender not in config/email-alerts.yaml"
        return out
    parser = PARSERS.get(sid)
    if not parser:
        out["skipped"] = f"no parser yet for sender {sid}"
        return out
    out["cards"] = parser(_plain(msg))
    return out


# ---------- mailbox (read-only) ----------

def _load_state() -> dict:
    p = project_path("state") / STATE_FILE
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(st: dict) -> None:
    (project_path("state") / STATE_FILE).write_text(json.dumps(st, indent=2), encoding="utf-8")


def fetch_new(imap=None) -> tuple[list[tuple[int, bytes]], dict]:
    """[(uid, raw)] newer than the last processed UID, oldest first. EXAMINE only; BODY.PEEK keeps them unread."""
    from . import mailer
    box = mailer.mailbox()
    folder = (alerts_config().get("mailbox") or {}).get("folder", "Career Buddy Alertas")
    if imap is None:
        if "unittest" in sys.modules:
            raise RuntimeError("test run: real mailbox access is disabled")
        imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        imap.login(box["primary_address"], mailer._password())
    try:
        typ, _ = imap.select(f'"{folder}"', readonly=True)
        if typ != "OK":
            raise RuntimeError(f"folder {folder!r} not found")
        validity = (imap.response("UIDVALIDITY")[1] or [b"0"])[0]
        validity = validity.decode() if isinstance(validity, bytes) else str(validity)
        st = _load_state()
        last = int(st.get("last_uid", 0)) if st.get("uidvalidity") == validity else 0
        typ, data = imap.uid("SEARCH", None, f"UID {last + 1}:*")
        uids = sorted(int(u) for u in (data[0] or b"").split() if int(u) > last)[-MAX_MESSAGES_PER_RUN:]
        out = []
        for u in uids:
            typ, d = imap.uid("FETCH", str(u), "(BODY.PEEK[])")
            raw = next((x[1] for x in d if isinstance(x, tuple)), None)
            if raw:
                out.append((u, raw))
        return out, {"uidvalidity": validity, "last_uid": max([last] + uids)}
    finally:
        try:
            imap.logout()
        except Exception:
            pass


def run(now, imap=None, messages=None) -> dict:
    """Read new alert e-mails and return a shortlist in the sweep's format. `messages` = [(uid, raw)] for tests."""
    if not config()["features"].get("email_alerts"):
        return {"skipped": "features.email_alerts is false", "shortlist": []}
    new_state = None
    if messages is None and imap is None and "unittest" in sys.modules:
        return {"skipped": "test run: real mailbox access is disabled", "shortlist": []}
    if messages is None:
        try:
            messages, new_state = fetch_new(imap)
        except Exception as e:          # mailbox down must never break the sweep
            state.event("mail_alerts_failed", message=f"{type(e).__name__}: {str(e)[:200]}")
            return {"error": f"{type(e).__name__}: {str(e)[:200]}", "shortlist": []}
    stats = {"messages": len(messages), "parsed": 0, "skipped_by_domain": {}, "cards": 0, "known_unchanged": 0,
             "logged_by_title": 0, "out_of_zone": 0, "shortlisted": 0, "no_cards": []}
    shortlist = []
    cfg = alerts_config()
    for uid, raw in messages:
        m = parse_message(raw, cfg)
        if not m["sender"] or m.get("skipped"):
            stats["skipped_by_domain"][m["from_domain"]] = stats["skipped_by_domain"].get(m["from_domain"], 0) + 1
            continue
        stats["parsed"] += 1
        if not m["cards"]:
            stats["no_cards"].append({"uid": uid, "sender": m["sender"], "subject": m["subject"]})
        for c in m["cards"]:
            stats["cards"] += 1
            chk = seen.check(c["url"], c["card_text"], c["company"], c["title"], c["location"])
            if chk["status"] == "known_unchanged":
                stats["known_unchanged"] += 1
                continue
            tri = targets.triage(c["title"], c["location"], strict=True)
            if not tri["read_detail"]:
                key = "out_of_zone" if tri["zone"]["status"] == "out_of_zone" else "logged_by_title"
                stats[key] += 1
                seen.add(c["url"], c["card_text"], "excluded", f"{tri['seen_destination_if_not_read']}; {tri['reason']} "
                         f"(e-mail alert, card only)", c["company"], c["title"], c["location"],
                         rule="C1" if key == "out_of_zone" else "T0")
                continue
            stats["shortlisted"] += 1
            shortlist.append({"source": f"MAIL-{m['sender'].upper()}", "channel": "email_alert",
                              "url": c["url"], "title": c["title"], "company": c["company"],
                              "location": c["location"], "closing": "", "zone": tri["zone"]["status"],
                              "group": tri["group"], "catalogue_title": tri["catalogue_title"],
                              "seen_status": chk["status"], "why": tri["reason"],
                              "read_detail_allowed": False, "card_text": c["card_text"],
                              "note": "alert link is a tracking redirect: never opened by the system; the user clicks it"})
    if new_state:
        _save_state({**new_state, "at": now_iso()})
    rec = {"at": now_iso(), **stats}
    state._append("mail-alerts-runs.jsonl", rec)
    return {**stats, "shortlist": shortlist}


def peek() -> list[dict]:
    """What the next run would read, without recording anything (state, seen) and without opening links."""
    msgs, _ = fetch_new()          # fetch_new never saves state; only run() does
    cfg = alerts_config()
    out = []
    for uid, raw in msgs:
        m = parse_message(raw, cfg)
        out.append({"uid": uid, "sender": m["sender"], "from_domain": m["from_domain"], "subject": m["subject"],
                    "skipped": m.get("skipped"),
                    "cards": [{k: c[k] for k in ("title", "company", "location", "salary")} for c in m["cards"]]})
    return out
