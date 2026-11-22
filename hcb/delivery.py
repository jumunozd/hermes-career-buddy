"""Package delivery by e-mail (P-10 D-P10-2). No LLM.

After the Writer and Recruiter rounds, the PM runs `bin/hcb deliver-email --folder <published vN>`: one e-mail
to the user with the documents attached and a short Spanish summary (verdict, send readiness, A-H fit,
missing facts). The user always submits the application; this only puts the package in his inbox.
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


def documents(folder: Path) -> list[Path]:
    """PDF first (to read on the phone), then DOCX (to edit or upload), in DOC_ORDER."""
    out = []
    for ext in ("pdf", "docx"):
        for stem in DOC_ORDER:
            out += sorted(p for p in folder.glob(f"{stem}*.{ext}") if p.is_file())
    return out


def _latest_review(prep: Path, version_label: str) -> dict | None:
    cands = sorted(prep.glob(f"recruiter-review-{version_label}-r*.json"))
    cands = [c for c in cands if "defective" not in c.name]
    return _load(cands[-1]) if cands else None


def compose(folder: Path, review: dict | None = None, fit: str | None = None, url: str | None = None,
            title: str | None = None, company: str | None = None) -> dict:
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
    docs = documents(folder)
    if not docs:
        raise ValueError("no PDF or DOCX in the version folder")
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
                 resend=False, dry_run=False, smtp=None) -> dict:
    review = _load(Path(review_path)) if review_path else None
    try:
        m = compose(Path(folder), review, fit, url, title, company)
    except ValueError as e:
        return {"status": "not_sent", "reason": str(e)}
    res = mailer.send(m["key"], m["subject"], m["body"], m["attachments"], what="application_package",
                      resend=resend, smtp=smtp, dry_run=dry_run)
    if dry_run:
        res["body"] = m["body"]
    return {"version_id": m["version_id"], "ready": m["ready"], **res}
