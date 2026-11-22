"""Opportunity -> Baserow row (P-6 schema v2), shared by the Job Hunter registration and the one-time backfill.

Only non-discarded offers go to Baserow (the user, 2026-11-19). The mapping is deterministic: one field per
fact, select values by name (hcb.baserow.build_payload turns them into option ids). The `[hcb v1]` tag block
stays in Notes as an audit mirror.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from . import baserow, daily, targets
from .util import fold, project_path

COUNCIL_HOSTS = ("gcc.tas.gov.au", "devonport.tas.gov.au", "hobartcity.com.au", "launceston.tas.gov.au",
                 "burnie.tas.gov.au", "kingborough.tas.gov.au", "ccc.tas.gov.au", "centralcoast.tas.gov.au")


def source_of(url: str, pasted: bool = False) -> str:
    host = (urlparse(url or "").hostname or "").removeprefix("www.")
    if "seek.com" in host:
        return "SEEK (pasted)"
    if "linkedin.com" in host:
        return "LinkedIn (pasted)"
    if host.endswith("jobs.tas.gov.au"):
        return "TSS"
    if any(host.endswith(h) for h in COUNCIL_HOSTS):
        return "Council"
    return "SEEK (pasted)" if pasted else "Employer site"


def _date(value) -> str | None:
    m = re.match(r"\d{4}-\d{2}-\d{2}", str(value or ""))
    return m.group(0) if m else None


def _contact(o: dict) -> str | None:
    """Applications "Ad Contact": how to apply / whom the ad names (person + phone, and the application inbox)."""
    c = o.get("contacts") or daily.extract_contacts(o.get("ad_text", ""))
    parts = []
    if c.get("phones") and not o.get("no_approach_clause"):
        who = c["contact_names"][0] if c.get("contact_names") else "contacto del aviso"
        parts.append(f"{who}: {c['phones'][0]['raw']}")
    inbox = next((e for e in c.get("emails") or [] if is_inbox(e)), None) or o.get("apply_email")
    if inbox:
        parts.append(f"Postulación: {inbox}")
    return " · ".join(parts) or None


def fields_for(o: dict, status: str = "Discovered", latest_version: str | None = None,
               opportunity_ref: str | None = None, pasted: bool = False) -> dict:
    """Baserow fields for one kept opportunity, matched against TODAY's target catalogue."""
    m = targets.match_title(o.get("title", ""))
    cat = o.get("ranking_category") or "pendiente_revision"
    url = o.get("canonical_url") or o.get("url") or ""
    ref = opportunity_ref or str(daily.ref_of(o))
    f = {
        "Job Title": o.get("title"), "Company": o.get("employer"), "Job URL": url or None,
        "Location": o.get("location"), "Status": status, "Closing Date": _date(o.get("closing_date")),
        "Opportunity Ref": ref, "Ranking Category": cat, "Alignment Group": m.get("group") or "none",
        "Catalogue Title": m.get("catalogue_title"), "Review Reason": daily._review_reason(o) if cat == "pendiente_revision" else None,
        "Entry Signal": o.get("entry_signal") if o.get("entry_signal") in ("Strategic Entry", "Neutral") else None,
        "Fit": o.get("fit"), "Source": source_of(url, pasted), "Posted Date": _date(o.get("posted_at")),
        "Discovered": _date(o.get("discovered_at")), "Ad Contact": _contact(o), "Latest Version": latest_version,
    }
    f["Notes"] = baserow.encode_tags({"ref": ref, "cat": cat, "seen": f["Discovered"] or ""})
    return {k: v for k, v in f.items() if v not in (None, "")}


def kept(o: dict, today: str, exclude_titles: set[str] = frozenset()) -> bool:
    """Not discarded under today's rules: open, in the catalogue, no excluded title word, not another field."""
    t = o.get("title", "")
    if o.get("estado") == "Cerrada" or fold(t) in {fold(x) for x in exclude_titles}:
        return False
    if (o.get("closing_date") or "9999-12-31") < today:
        return False
    if targets.excluded_by_title(t):
        return False
    if any(targets._stem_rx(w).search(fold(t)) for w in targets.catalogue().get("out_of_field_titles", [])):
        return False
    portal = daily.portal_card(o)
    if "revisar funciones" in (daily._review_reason(o) or "") and not portal:
        return False
    if portal:   # 2026-11-22: an alert card has no duties to judge; the user sends the ad (📎) before preparing
        return bool(targets.match_title(t).get("group") or targets.aligned_tokens(t))
    return bool(targets.match_title(t).get("group"))


def latest_version(opp_dir: Path) -> str | None:
    best = None
    for prep in sorted(p for p in opp_dir.iterdir() if p.is_dir()):
        for v in prep.glob("v[0-9]*"):
            n = int(v.name[1:])
            if best is None or n > best[0]:
                best = (n, f"{prep.name}/{v.name}")
    return best[1] if best else None


def load_snapshots(paths: list[Path]) -> list[dict]:
    seen = {}
    for p in paths:
        for o in json.loads(p.read_text(encoding="utf-8")).get("opportunities", []):
            seen[(fold(o.get("employer", "")), fold(o.get("title", "")))] = o
    return list(seen.values())


def preview(rows: list[dict], live_rows: list[dict] | None = None, option_ids=None) -> list[dict]:
    """Dry-run payload per row, with the duplicate check against the live table (by Opportunity Ref or URL)."""
    live_rows = live_rows if live_rows is not None else baserow.list_rows()
    refs = {r.get("Opportunity Ref") for r in live_rows if r.get("Opportunity Ref")}
    urls = {(r.get("Job URL") or "").rstrip("/").lower() for r in live_rows if r.get("Job URL")}
    out = []
    for f in rows:
        dup = f["Opportunity Ref"] in refs or (f.get("Job URL") or "").rstrip("/").lower() in urls
        out.append({"fields": f, "duplicate": dup, "payload": None if dup else baserow.build_payload(f, option_ids)})
    return out


def backfill_rows(today: str) -> list[dict]:
    """P-6 step 5: the offers kept from earlier runs + every prepared package (state Preparing)."""
    snaps = sorted((project_path("state") / "snapshots").glob("*.json"))
    snaps = [p for p in snaps if not p.name.startswith("prueba")]
    spec_path = project_path("state") / "backfill-p6.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8")) if spec_path.exists() else {}
    exclude = set(spec.get("exclude_titles", []))
    rows = [fields_for(o) for o in load_snapshots(snaps) if kept(o, today, exclude)]
    apps = project_path("applications")
    for p in spec.get("prepared", []):
        rows.append(fields_for(p, status="Preparing", latest_version=latest_version(apps / p["folder"]),
                               opportunity_ref=p["opportunity_ref"], pasted=True))
    return rows


def register_snapshot(path, today: str, live: bool, live_rows=None, writer=None, option_ids=None) -> dict:
    """Weekday run: register the snapshot's NON-DISCARDED offers in Baserow (one row each, never twice) and
    write each Baserow row id back into the snapshot (`baserow_id`), so the digest shows the real ID."""
    path = Path(path)
    snap = json.loads(path.read_text(encoding="utf-8"))
    live_rows = live_rows if live_rows is not None else baserow.list_rows()
    by_ref = {r.get("Opportunity Ref"): r["id"] for r in live_rows if r.get("Opportunity Ref")}
    # 2026-11-22: the same vacancy from another channel (e-mail alert vs the employer page) has another ref and
    # a differently written location: an open row with the same employer + title is the same offer.
    _st = lambda r: (r.get("Status") or {}).get("value") if isinstance(r.get("Status"), dict) else r.get("Status")
    by_job = {(fold(r.get("Company") or ""), fold(r.get("Job Title") or "")): r["id"] for r in live_rows
              if _st(r) not in ("Closed", "Rejected", "Withdrawn")}
    status_of = {r["id"]: _st(r) for r in live_rows}
    writer = writer or baserow.write
    results = []
    for o in snap.get("opportunities", []):
        if o.get("baserow_id") not in (None, ""):
            continue
        if not kept(o, today):
            results.append({"title": o.get("title"), "action": "not_registered", "why": "discarded by today's rules"})
            continue
        f = fields_for(o)
        ref = f["Opportunity Ref"]
        if ref in by_ref:
            o["baserow_id"] = by_ref[ref]
            o["tracked_status"] = status_of.get(by_ref[ref])
            results.append({"ref": ref, "action": "already_in_baserow", "row_id": by_ref[ref]})
            continue
        same = by_job.get((fold(f.get("Company") or ""), fold(f.get("Job Title") or "")))
        if same:
            o["baserow_id"] = same
            o["tracked_status"] = status_of.get(same)        # the digest skips offers already being prepared
            results.append({"ref": ref, "action": "already_in_baserow", "row_id": same, "why": "same employer and title"})
            continue
        baserow.build_payload(f, option_ids)          # validate before any write
        r = writer("create", f, "register:" + ref, live=live, task_id="register")
        if r.get("write_performed") or r.get("skipped"):
            rid = r.get("row_id") or (r.get("result_ref") and int(r["result_ref"]))
            if rid:
                o["baserow_id"] = rid
                by_ref[ref] = rid
        results.append({"ref": ref, "action": "created" if r.get("write_performed") else r.get("mode", r.get("skipped")),
                        "row_id": o.get("baserow_id"), "verified": r.get("verified")})
    if live:
        path.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"snapshot": str(path), "live": live, "results": results}


# ---------- P-7: documents and contacts ----------
# Contacts = PEOPLE the user may network with (the user, 2026-11-19). Generic application channels
# (careers@, recruitment@, a switchboard number) belong to the offer: Applications "Ad Contact".
_INBOX = re.compile(r"(?i)^(recruitment|recruiting|careers|career|jobs|job|hr|talent|people|corporate|info|enquiries|admin|apply)[._-]?[a-z]*@")


def is_inbox(email: str) -> bool:
    return bool(_INBOX.match(email or ""))

DOC_TYPES = [(re.compile(r"^cv-"), "CV"), (re.compile(r"^cover-letter"), "Cover letter"),
             (re.compile(r"^selection-criteria"), "Selection criteria"), (re.compile(r"^outreach"), "Outreach note"),
             (re.compile(r"interview.*brief|preparation-brief"), "Interview brief"),
             (re.compile(r"interview.*simulation|voice-simulation"), "Interview simulation")]


def document_rows(version_dir: Path, opportunity_ref: str, company: str, app_row_id: int | None) -> list[dict]:
    """One Documents row per delivered PDF of a published version, with the SHA256 from its manifest."""
    version_dir = Path(version_dir)
    man = json.loads((version_dir / "manifest.json").read_text(encoding="utf-8")) if (version_dir / "manifest.json").exists() else {}
    sha = {f["file"]: f.get("sha256") for f in man.get("files", [])}
    pkg = f"{version_dir.parent.name}/{version_dir.name}"
    rows = []
    for pdf in sorted(version_dir.glob("*.pdf")):
        dtype = next((t for rx, t in DOC_TYPES if rx.search(pdf.stem)), None)
        if not dtype:
            continue
        rows.append({"_file": str(pdf), "Document Name": f"{dtype} - {company} - {pkg}", "Document Type": dtype,
                     "Version": int(re.sub(r"\D", "", version_dir.name) or 0), "Package Version": pkg,
                     "SHA256": sha.get(pdf.name) or "", "Approved": False, "Opportunity Ref": opportunity_ref,
                     "Application": app_row_id, "Notes": f"local: private/applications/{version_dir.parent.parent.name}/{pkg}/{pdf.name}"})
    return rows


def contact_rows(ad_text: str, company: str, app_row_id: int | None, research: list[dict] | None = None,
                 no_approach: bool = False, source_url: str | None = None, contacts: dict | None = None) -> list[dict]:
    """Contacts printed in the ad + researched ones (P-2, max 2). Never contacted by the system."""
    c = contacts or daily.extract_contacts(ad_text or "")
    approach = "no-approach clause" if no_approach else "allowed"
    rows = []
    names, phones = c.get("contact_names") or [], c.get("phones") or []
    for i, ph in enumerate(phones[:2]):
        if i >= len(names):                   # a phone with no person named is an application channel
            continue
        rows.append({"Name": names[i], "Company": company,
                     "Channel": "Phone (ad)", "Phone": ph["raw"], "Source URL": source_url, "Confidence": "confirmed",
                     "Origin": "Ad", "Approach": approach, "Application": app_row_id})
    for e in (c.get("emails") or [])[:2]:
        if is_inbox(e) or not names:          # application inbox: lives in Applications, not in Contacts
            continue
        rows.append({"Name": names[0], "Company": company, "Channel": "Business email", "Email": e,
                     "Source URL": source_url, "Confidence": "confirmed", "Origin": "Ad", "Approach": approach,
                     "Application": app_row_id})
    for r in (research or [])[:2]:
        if not r.get("name") or is_inbox(r.get("professional_email") or ""):
            continue                          # a person is required (the user, 2026-11-19)
        ch = ("Business email" if r.get("professional_email") and r.get("email_status") == "verified_public_business"
              else "LinkedIn" if r.get("linkedin_url") else "Other")
        rows.append({"Name": r.get("name") or "Canal oficial", "Company": r.get("employer") or company, "Role": r.get("title"),
                     "Channel": ch, "Email": r.get("professional_email") if ch == "Business email" else None,
                     "Source URL": r.get("linkedin_url") or r.get("source_url"),
                     "Confidence": "confirmed" if r.get("confidence") == "confirmed" else "inferred",
                     "Origin": "Research", "Approach": approach, "Application": app_row_id})
    # One row per PERSON (the user, 2026-11-19: a phone and an e-mail of the same person are one contact);
    # generic inboxes are one row per address. A channel value seen twice is kept once.
    out, by_person, seen_vals = [], {}, set()
    for row in rows:
        row = {k: v for k, v in row.items() if v not in (None, "")}
        vals = {str(row.get(k)).lower() for k in ("Phone", "Email") if row.get(k)}
        if vals and vals <= seen_vals:
            continue
        seen_vals |= vals
        person = row.get("Name") if row.get("Name") not in ("Contacto del aviso", "Canal de empleo", "Canal oficial") else None
        key = (person or "").lower(), str(row.get("Application"))
        if person and key in by_person:
            merged = by_person[key]
            for k in ("Phone", "Email", "Role", "Source URL"):
                merged.setdefault(k, row.get(k)) if row.get(k) else None
            continue
        if person:
            by_person[key] = row
        out.append(row)
    return out


def _research_for(ref: str, folder: str | None = None) -> list[dict]:
    base = project_path("state") / "research"
    for name in filter(None, (ref, folder, (folder or "").upper())):
        f = base / name / "contacts.json"
        if f.exists():
            d = json.loads(f.read_text(encoding="utf-8"))
            return d.get("contacts") or []
    return []


def p7_backfill(app_rows: list[dict] | None = None) -> dict:
    """Documents for every prepared package (latest version) + contacts for every Applications row."""
    app_rows = app_rows if app_rows is not None else baserow.list_rows()
    by_ref = {r.get("Opportunity Ref"): r for r in app_rows if r.get("Opportunity Ref")}
    spec = json.loads((project_path("state") / "backfill-p6.json").read_text(encoding="utf-8"))
    folders = {p["opportunity_ref"]: p["folder"] for p in spec.get("prepared", [])}
    apps, ads = project_path("applications"), project_path("state") / "ads"
    snaps = load_snapshots(sorted((project_path("state") / "snapshots").glob("*.json")))
    docs, contacts = [], []
    for ref, row in by_ref.items():
        company = row.get("Company") or ""
        folder = folders.get(ref)
        if folder and (apps / folder).exists():
            lv = latest_version(apps / folder)
            if lv:
                docs += document_rows(apps / folder / lv, ref, company, row["id"])
        ad_text = (ads / f"{folder}.txt").read_text(encoding="utf-8") if folder and (ads / f"{folder}.txt").exists() else ""
        o = next((s for s in snaps if str(daily.ref_of(s)) == ref), None)
        if o:
            ad_text = o.get("ad_text") or ad_text
        contacts += contact_rows(ad_text, company, row["id"], _research_for(ref, folder),
                                 no_approach=bool(o and o.get("no_approach_clause")), source_url=row.get("Job URL"),
                                 contacts=(o or {}).get("contacts"))
    return {"documents": docs, "contacts": contacts}


def write_p7(rows: dict, live: bool, existing_docs=None, existing_contacts=None, uploader=None, writer=None) -> dict:
    """Write Documents (file uploaded) and Contacts rows, skipping ones already present (same SHA256 /
    same channel value on the same offer). Preview unless live."""
    existing_docs = existing_docs if existing_docs is not None else baserow.table_rows("documents")
    existing_contacts = existing_contacts if existing_contacts is not None else baserow.table_rows("contacts")
    uploader = uploader or baserow.upload_file
    writer = writer or baserow.write_table
    have_sha = {r.get("SHA256") for r in existing_docs if r.get("SHA256")}
    def ckey(r):
        app = r.get("Application")
        app = app[0]["id"] if isinstance(app, list) and app and isinstance(app[0], dict) else (app[0] if isinstance(app, list) and app else app)
        return (str(app), (r.get("Phone") or r.get("Email") or r.get("Source URL") or "").lower())
    def cvals(r):
        app = ckey(r)[0]
        return {(app, str(r.get(k)).lower()) for k in ("Phone", "Email") if r.get(k)}
    have_c = {ckey(r) for r in existing_contacts}
    have_vals = set().union(*[cvals(r) for r in existing_contacts]) if existing_contacts else set()
    out = {"documents": [], "contacts": []}
    for d in rows.get("documents", []):
        f = {k: v for k, v in d.items() if not k.startswith("_")}
        if f.get("SHA256") and f["SHA256"] in have_sha:
            out["documents"].append({"name": f["Document Name"], "action": "already_in_baserow"}); continue
        if live:
            f["File"] = uploader(d["_file"])
        r = writer("documents", "create", f, "p7-doc:" + (f.get("SHA256") or f["Document Name"]), live=live, task_id="p7")
        out["documents"].append({"name": f["Document Name"], "action": "created" if r.get("write_performed") else r.get("mode", r.get("skipped")),
                                 "row_id": r.get("row_id"), "verified": r.get("verified")})
    for c in rows.get("contacts", []):
        k = ckey(c)
        if k in have_c or (cvals(c) and cvals(c) <= have_vals):
            out["contacts"].append({"name": c.get("Name"), "action": "already_in_baserow"}); continue
        r = writer("contacts", "create", c, f"p7-contact:{k[0]}:{k[1]}", live=live, task_id="p7")
        have_c.add(k)
        out["contacts"].append({"name": c.get("Name"), "channel": c.get("Channel"),
                                "action": "created" if r.get("write_performed") else r.get("mode", r.get("skipped")),
                                "row_id": r.get("row_id"), "verified": r.get("verified")})
    return out
