"""Package delivery by e-mail (P-10 D-P10-2). No LLM.

Review first, e-mail second (the user, 2026-11-25): after the Writer and Recruiter rounds the PM runs
`bin/hcb package-show --folder <published vN>`, which lists every document as a PDF for Telegram (MEDIA lines)
and records `package_shown`. The user checks them there, asks for changes if needed, and only when he writes
«Correo <ID>» the PM runs `bin/hcb deliver-email --folder <vN> --confirmed "<his message>"`. The code refuses
the e-mail without a Telegram review of that version and without that confirmation. One e-mail, only to the
user, with every document as a PDF (DOCX only with --with-docx). The user always submits the application.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import mailer

DOC_ORDER = ["cv", "cover-letter", "selection-criteria", "statement"]


def _load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def split_application(label: str) -> tuple[str, str]:
    """'TasPorts, Project Controls Officer (Hobart)' -> ('Project Controls Officer', 'TasPorts')."""
    label = re.sub(r"^SYNTHETIC TEST ONLY:\s*", "", label or "").strip()
    if ", " not in label:
        return label, ""
    company, role = label.split(", ", 1)
    if re.search(r"\b(Pty|Ltd|Inc)\b", role.split(",")[0]) and ", " in role:   # "X (Aust) Pty Ltd, Role"
        extra, role = role.split(", ", 1)
        company = f"{company}, {extra}"
    role = re.sub(r"\s*\([^)]*\)\s*$", "", role).strip()
    return role, company.strip()


def documents(folder: Path, with_docx: bool = False) -> list[Path]:
    """Every document as a PDF, in DOC_ORDER (then DOCX only when asked). A document that exists only as DOCX
    (or md/html) has no PDF: that is an error, never a silent omission."""
    out = []
    for ext in ("pdf", "docx") if with_docx else ("pdf",):
        for stem in DOC_ORDER:
            out += sorted(p for p in folder.glob(f"{stem}*.{ext}") if p.is_file())
    return out


def missing_pdfs(folder: Path) -> list[str]:
    """Documents of the version (docx/md) whose PDF is missing."""
    stems = {p.stem for stem in DOC_ORDER for ext in ("docx", "md") for p in folder.glob(f"{stem}*.{ext}")}
    return sorted(s for s in stems if not (folder / f"{s}.pdf").is_file())


def _vkey(folder: Path, man: dict) -> str:
    return str(man.get("version_id") or Path(folder).resolve())


def _ref_of(folder: Path, man: dict) -> str:
    return str(man.get("opportunity_ref") or folder.parent.parent.name)


def show(folder) -> dict:
    """The Telegram review step: every PDF as a MEDIA line, recorded as shown for this version."""
    from . import state
    folder = Path(folder).resolve()
    man = _load(folder / "manifest.json")
    if not man:
        return {"status": "not_shown", "reason": "not a published version (manifest.json missing)"}
    miss = missing_pdfs(folder)
    if miss:
        return {"status": "not_shown", "reason": "documents without PDF: " + ", ".join(miss)}
    docs = documents(folder)
    if not docs:
        return {"status": "not_shown", "reason": "no PDF in the version folder"}
    ref = _ref_of(folder, man)
    state.event("package_shown", ref=ref, version_id=man.get("version_id"), version_key=_vkey(folder, man),
                folder=str(folder),
                files=[d.name for d in docs])
    media = "\n".join(f"MEDIA:{d}" for d in docs)
    return {"status": "shown", "ref": ref, "version_id": man.get("version_id"), "files": [d.name for d in docs],
            "media_lines": media,
            "ask_user": f"Revisa los documentos. Si quieres cambios: «Cambios {ref}: ...». "
                        f"Cuando estén bien, escribe «Correo {ref}» y te los mando a tu correo en PDF."}


def check_confirmation(folder: Path, man: dict, confirmed: str | None) -> str | None:
    """None if the e-mail may go; otherwise the reason it may not."""
    from . import commands, state
    ref = _ref_of(folder, man)
    shown = [e for e in state._read("events.jsonl") if e.get("kind") == "package_shown"
             and e.get("version_key") == _vkey(folder, man)]
    if not shown:
        return (f"version {man.get('version_id') or folder.name} was not shown in Telegram first: run bin/hcb package-show "
                f"--folder <vN> and wait for «Correo {ref}»")
    if not confirmed:
        return f"needs the user's confirmation: --confirmed \"<his message, e.g. Correo {ref}>\""
    p = commands.parse(confirmed)
    if p.get("intent") != "email_package":
        return f"the message {confirmed[:80]!r} is not an e-mail confirmation (expected «Correo {ref}»)"
    if p.get("ref") and str(p["ref"]) != ref:
        return f"the confirmation is for offer {p['ref']}, this version is offer {ref}"
    return None


def _latest_review(prep: Path, version_label: str) -> dict | None:
    cands = sorted(prep.glob(f"recruiter-review-{version_label}-r*.json"))
    cands = [c for c in cands if "defective" not in c.name]
    return _load(cands[-1]) if cands else None


def compose(folder: Path, review: dict | None = None, fit: str | None = None, url: str | None = None,
            title: str | None = None, company: str | None = None, with_docx: bool = False) -> dict:
    folder = Path(folder)
    man = _load(folder / "manifest.json")
    if not man:
        raise ValueError("not a published version (manifest.json missing): run bin/hcb engine publish first")
    content = _load(folder / "content.json") or {}
    t, c = split_application(content.get("application", ""))
    title, company = title or t, company or c
    review = review if review is not None else _latest_review(folder.parent, man.get("version_label", ""))
    readiness = (review or {}).get("send_readiness")
    ready = readiness == "ready_for_human_review"
    miss = missing_pdfs(folder)
    if miss:
        raise ValueError("documents without PDF: " + ", ".join(miss))
    docs = documents(folder, with_docx)
    if not docs:
        raise ValueError("no PDF in the version folder")
    subject = (f"Application Ready: {title} | {company}" if ready
               else f"Application Draft, needs your input: {title} | {company}")
    lines = [f"{title}", f"{company}"]
    if url:
        lines.append(f"Aviso: {url}")
    lines.append("")
    lines.append(f"Versión: {man.get('version_id', man.get('version_label'))} (ref. {man.get('opportunity_ref')})")
    if fit:
        lines.append(f"Fit A-H: {fit}")
    if review:
        lines.append(f"Recruiter: {review.get('verdict', 'sin veredicto')} (ronda {review.get('round', '?')})")
        for r in (review.get("principal_reasons") or [])[:3]:
            txt = r.get("reason") if isinstance(r, dict) else str(r)
            lines.append(f"  - {txt[:300]}")
    else:
        lines.append("Recruiter: sin revisión registrada para esta versión.")
    lines.append("Estado: lista para que la revises y la envíes tú." if ready
                 else "Estado: NO marcada como lista para enviar. Revisa las preguntas de abajo antes de usarla.")
    mfr = _load(folder / "missing-fact-requests.json") or []
    if mfr:
        lines += ["", "Datos que faltan (agrégalos al banco de hechos, private/facts, y pide «Cambios»):"]
        for m in mfr[:6]:
            lines.append(f"  - {m.get('claim_needed', '')[:280]}")
    outreach = sorted((folder.parent / "outreach").glob("outreach-*.md")) if (folder.parent / "outreach").is_dir() else []
    if outreach:
        lines += ["", "Nota de contacto preparada (la envías tú, si quieres):", outreach[-1].read_text(encoding="utf-8")[:1500]]
    lines += ["", "Adjuntos: " + ", ".join(d.name for d in docs),
              "", "El sistema nunca envía postulaciones ni contacta a nadie. Cuando la envíes, escribe «Enviada <ID>» en Telegram.",
              "Hermes Career Buddy"]
    return {"key": f"package:{man.get('version_id') or folder}", "subject": subject, "body": "\n".join(lines),
            "attachments": docs, "ready": ready, "version_id": man.get("version_id")}


def send_package(folder, review_path=None, fit=None, url=None, title=None, company=None,
                 resend=False, dry_run=False, smtp=None, confirmed=None, with_docx=False) -> dict:
    review = _load(Path(review_path)) if review_path else None
    folder = Path(folder).resolve()
    man = _load(folder / "manifest.json")
    if man and not dry_run:
        why = check_confirmation(folder, man, confirmed)
        if why:
            return {"status": "not_sent", "reason": why}
    try:
        m = compose(folder, review, fit, url, title, company, with_docx)
    except ValueError as e:
        return {"status": "not_sent", "reason": str(e)}
    res = mailer.send(m["key"], m["subject"], m["body"], m["attachments"], what="application_package",
                      resend=resend, smtp=smtp, dry_run=dry_run)
    if dry_run:
        res["body"] = m["body"]
    return {"version_id": m["version_id"], "ready": m["ready"], **res}
