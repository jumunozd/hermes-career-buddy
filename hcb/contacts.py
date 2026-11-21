"""Early-hiring contacts (P-2, AP-ea17780d4846d8c90c64ab11).

Split of work:
- Job Hunter: `policy()` on every new ad (deterministic, ~0 tokens): contacts printed in the ad,
  employer type (agency / government / private) and any "no approaches" clause.
- PM: `trigger()` decides which new offers get Research `contact_research` (token cap).
- Research Agent: finds at most 2 people from public sources; `validate()` enforces the data rules.
- Writer drafts an outreach note only on `Prepara contacto [ID]`; `outreach_lint()` checks its shape.
Nothing here sends or contacts anyone: the user does (D-PM-03).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

from .daily import extract_contacts, hours_since
from .util import ROOT, fold, load_yaml

_POL = None


def cfg() -> dict:
    global _POL
    if _POL is None:
        _POL = load_yaml(ROOT / "config" / "contact-policy.yaml")
    return _POL


def _word_hit(names: list[str], text: str) -> str | None:
    for n in names:
        if re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", text):
            return n
    return None


def employer_type(employer: str, ad_text: str) -> dict:
    c = cfg()
    emp, ad = fold(employer or ""), fold(ad_text or "")
    hit = _word_hit(c["agency_names"], emp) or next((p for p in c["agency_phrases"] if re.search(p, ad)), None)
    if hit:
        return {"employer_type": "agency", "basis": hit}
    hit = _word_hit(c["government_names"], emp) or next((p for p in c["government_phrases"] if re.search(p, ad)), None)
    if hit:
        return {"employer_type": "government", "basis": hit}
    return {"employer_type": "private", "basis": None}


def no_approach_clause(ad_text: str) -> str | None:
    for line in (ad_text or "").splitlines():
        fl = fold(line)
        if any(re.search(p, fl) for p in cfg()["no_approach_patterns"]):
            return line.strip()[:160]
    return None


_GENERIC_INBOX = re.compile(r"^(recruit\w*|careers?|jobs?|hr|people|talent\w*|employment|apply|vacanc\w*)[@.]", re.I)


def from_ad(ad: dict) -> list[dict]:
    """Contacts the employer itself printed in the ad: always confirmed, no LLM, no research."""
    out = []
    for n in ad["contact_names"][:2]:
        out.append({"priority": "ad_named", "name": n, "confidence": "confirmed", "source_url": "ad",
                    "phone_from_ad": ad["phones"][0]["raw"] if ad["phones"] else None})
    for e in ad["emails"]:
        if len(out) >= 2:
            break
        generic = bool(_GENERIC_INBOX.match(e))
        out.append({"priority": "careers_inbox" if generic else "ad_named", "professional_email": e,
                    "email_status": "verified_public_business", "email_source_url": "ad",
                    "confidence": "confirmed", "source_url": "ad"})
    return out


def policy(ad_text: str, employer: str) -> dict:
    """What the Job Hunter attaches to every new record."""
    et = employer_type(employer, ad_text)
    clause = no_approach_clause(ad_text)
    # A no-approach clause leaves only the official channel (careers inbox / portal).
    allowed = ["careers_inbox"] if clause else list(cfg()["allowed_by_employer_type"][et["employer_type"]])
    ad = extract_contacts(ad_text)
    return {**et, "no_approach_clause": clause, "allowed_priorities": allowed,
            "max_contacts": cfg()["max_contacts"], "ad_contacts": ad,
            "from_ad": from_ad(ad),
            # Research only adds value where it may look beyond the ad (private employers).
            "people_research_allowed": not clause and bool({"hiring_manager", "talent_acquisition"} & set(allowed)),
            "note": "Formal application via the ad's channel is always required; outreach only complements it."}


def trigger(opportunities: list[dict], now: datetime) -> dict:
    """Which new offers get Research `contact_research` this run (P-2 §2). Deterministic."""
    c = cfg()
    cutoff = now - timedelta(hours=c["fresh_hours"])
    run, skip = [], []
    for o in opportunities:
        why = []
        disc = o.get("discovered_at")
        if not disc or datetime.fromisoformat(disc) < cutoff:
            why.append("not new in this window")
        age = hours_since(o.get("posted_at"), now)
        if age is not None and age > c["fresh_hours"]:
            why.append(f"posted {age:.0f} h ago (> {c['fresh_hours']} h)")
        cat = o.get("ranking_category")
        if not (cat == "principal" or (cat == "exploratoria" and o.get("entry_signal") == "Strategic Entry")):
            why.append(f"category {cat} / entry {o.get('entry_signal')} not eligible")
        if o.get("ah_recommendation") == "DO_NOT_RECOMMEND" and not o.get("ah_override"):
            why.append("A-H DO_NOT_RECOMMEND without user override")
        ref = o.get("opportunity_ref") or o.get("baserow_id")
        if o.get("research_contacts") or (ref and (ROOT / "state" / "research" / str(ref) / "contacts.json").exists()):
            why.append("contacts already researched for this offer")
        if o.get("outreach_status") in ("drafted", "sent_by_user") or o.get("employer_contacted_before"):
            why.append("The user already contacted / has a draft for this employer: no new introduction")
        pol = policy(o.get("ad_text", ""), o.get("employer", ""))
        if pol["no_approach_clause"]:
            why.append(f"no-approach clause: {pol['no_approach_clause']}")
        named = len(pol["ad_contacts"]["contact_names"])
        if named >= c["max_contacts"]:
            why.append("ad already names 2 contacts")
        if not pol["people_research_allowed"] and not pol["no_approach_clause"]:
            why.append(f"{pol['employer_type']} employer: use only the ad's contacts ({len(pol['from_ad'])} found)")
        item = {"baserow_id": o.get("baserow_id"), "employer": o.get("employer"), "title": o.get("title"),
                "fit": o.get("fit"), "hours_since_posted": age, "policy": pol,
                "contacts_needed": max(0, c["max_contacts"] - named)}
        (skip if why else run).append({**item, "skip_reasons": why} if why else item)
    run.sort(key=lambda i: (-(i["fit"] or 0), i["hours_since_posted"] if i["hours_since_posted"] is not None else 999))
    over = run[c["max_offers_per_run"]:]
    for o in over:
        o["skip_reasons"] = [f"cap of {c['max_offers_per_run']} offers per run"]
    return {"run": run[:c["max_offers_per_run"]], "skipped": skip + over,
            "max_offers_per_run": c["max_offers_per_run"], "contact_performed": False}


def _domain(url_or_email: str) -> str:
    s = url_or_email.split("@", 1)[1] if "@" in url_or_email else (urlparse(url_or_email).hostname or "")
    return s.lower().removeprefix("www.")


def validate(result: dict, ad_text: str, employer: str) -> list[str]:
    """Data rules for a Research `contact_research` output (P-2 §3-4). Returns problems."""
    c = cfg()
    pol = policy(ad_text, employer)
    contacts = result.get("contacts", [])
    problems = []
    if len(contacts) > c["max_contacts"]:
        problems.append(f"{len(contacts)} contacts > max {c['max_contacts']}")
    for i, p in enumerate(contacts, 1):
        tag = f"contact {i} ({p.get('name') or p.get('priority')})"
        extra = set(p) - set(c["contact_fields"])
        if extra:
            problems.append(f"{tag}: fields not allowed {sorted(extra)}")
        if p.get("priority") not in c["priority"]:
            problems.append(f"{tag}: invalid priority {p.get('priority')!r}")
        elif p["priority"] not in pol["allowed_priorities"]:
            problems.append(f"{tag}: priority {p['priority']} not allowed for {pol['employer_type']}"
                            + (" (no-approach clause)" if pol["no_approach_clause"] else ""))
        need = ["source_url", "observed_at", "confidence"] + ([] if p.get("priority") == "careers_inbox"
                                                              else ["name", "title", "why_relevant"])
        for k in need:
            if not p.get(k):
                problems.append(f"{tag}: missing {k}")
        if p.get("confidence") not in (None, "confirmed", "inferred"):
            problems.append(f"{tag}: confidence must be confirmed|inferred")
        src = p.get("source_url") or ""
        if p.get("priority") == "hiring_manager" and "linkedin.com" in src and p.get("confidence") != "inferred":
            problems.append(f"{tag}: a LinkedIn profile alone cannot confirm the hiring manager (use inferred)")
        email = p.get("professional_email")
        if email:
            dom = _domain(email)
            if dom in c["personal_email_domains"]:
                problems.append(f"{tag}: personal email domain {dom} is never allowed")
            if p.get("email_status") != "verified_public_business" or not p.get("email_source_url"):
                problems.append(f"{tag}: email needs email_status=verified_public_business and email_source_url")
        elif p.get("email_status") not in (None, "not_verified"):
            problems.append(f"{tag}: email_status without an email")
        li = p.get("linkedin_url")
        if li and not re.match(r"https://(?:[a-z]{2,3}\.)?linkedin\.com/in/[\w\-%]+/?$", li):
            problems.append(f"{tag}: linkedin_url must be a public /in/ profile URL")
        if p.get("priority") == "ad_named":
            named = [fold(n) for n in pol["ad_contacts"]["contact_names"]]
            if p.get("name") and named and fold(p["name"]) not in named:
                problems.append(f"{tag}: ad_named but the ad names {pol['ad_contacts']['contact_names']}")
    for k in ("email_sent", "message_sent", "employer_contacted", "connection_request_sent"):
        if result.get(k):
            problems.append(f"out-of-role action reported: {k}")
    return problems


def outreach_lint(body: str) -> dict:
    """Shape of a short outreach note (P-2 §1, draft skill §10). Claims are checked by the Recruiter."""
    o = cfg()["outreach"]
    lines = [l for l in body.strip().splitlines() if l.strip()]
    greeting = lines[0] if lines and re.match(r"(?i)^(hi|hello|dear|good (morning|afternoon))\b", lines[0]) else None
    signoff_idx = next((i for i, l in enumerate(lines) if re.match(r"(?i)^(kind regards|regards|best regards|thanks|thank you|cheers)\b", l)), len(lines))
    body_lines = lines[1 if greeting else 0:signoff_idx]
    words = len(re.findall(r"\b\w[\w'-]*\b", " ".join(body_lines)))
    problems = []
    if not o["body_lines_min"] <= len(body_lines) <= o["body_lines_max"]:
        problems.append(f"body has {len(body_lines)} lines (allowed {o['body_lines_min']}-{o['body_lines_max']})")
    if words > o["body_words_max"]:
        problems.append(f"body has {words} words (> {o['body_words_max']})")
    if "—" in body:
        problems.append("em dash found")
    if re.search(r"(?i)hope (this|you).{0,20}(finds you|well)|i am writing to|to whom it may concern", body):
        problems.append("generic opener")
    if re.search(r"(?i)\b(attached|attachment)\b", body) and not re.search(r"(?i)\b(cv|resume)\b", body):
        problems.append("mentions an attachment without saying what it is")
    if len(re.findall(r"\?", " ".join(body_lines))) > 1:
        problems.append("more than one question/request")
    return {"body_lines": len(body_lines), "words": words, "ok": not problems, "problems": problems}
