"""User command parser (project-manager.md §6.2-6.3). Same parser for CLI and Telegram.

Commands are case- and accent-insensitive. An ambiguous command is never executed.
Natural-language equivalents are interpreted by the PM (LLM), which must confirm in
one line before writing anything; this parser only handles the fixed vocabulary.
"""
from __future__ import annotations

import re

from .util import fold

_ID = r"(?:id\s*)?(\d+)"


def _nums(text: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", text)]


def parse(message: str) -> dict:
    raw = message.strip()
    t = fold(raw)

    # The user sends the full ad for an offer the system may not read: "Aviso 27" + a PDF or the pasted text.
    m = re.match(r"\s*aviso (?:id\s*)?(\d{1,9}|o-[0-9a-f]{6})\b", t)
    if m:
        doc = re.search(r"saved at: (.+?\.(?:pdf|txt|md|html?))\b", raw, flags=re.I)
        rest = raw[m.end():].strip(" :\n") if not doc else ""
        return {"intent": "ad_supplied", "ref": m.group(1), "file": doc.group(1).strip() if doc else None,
                "has_text": len(rest) > 200, "authorises": "prepare_only", "blocks": ["send", "contact"],
                "next": "bin/hcb ad-save --ref <ref> --file <file> (or --text-file with the pasted text), "
                        "then bin/hcb prepare-request --ref <ref>"}

    m = re.fullmatch(r"prepara (?:la )?oferta (o-[0-9a-f]{6})", t)
    if m:  # digest code for an offer not yet in Baserow (dry-run period)
        return {"intent": "prepare", "by": "digest_ref", "values": [m.group(1)],
                "authorises": "prepare_only", "blocks": ["send", "contact"]}

    m = re.fullmatch(r"prepara (?:el )?contacto (o-[0-9a-f]{6})", t)
    if m:
        return {"intent": "prepare_contact", "digest_ref": m.group(1),
                "authorises": "outreach_draft_only", "blocks": ["send", "contact"]}

    # An ad saved by the user (pasted from SEEK/LinkedIn): "Prepara la oferta ... private/state/ads/<file>.txt"
    m = re.search(r"\b(?:private/)?state/ads/([a-z0-9][a-z0-9._-]{2,100}\.(?:txt|md))\b", t)
    if m and re.match(r"prepara (?:las? )?ofertas? ", t):
        from .util import project_path
        f = project_path("state") / "ads" / m.group(1)
        if not f.is_file():
            return {"intent": "error", "reason": f"no existe el aviso guardado {m.group(1)}"}
        return {"intent": "prepare", "by": "ad_file", "values": [str(f)],
                "authorises": "prepare_only", "blocks": ["send", "contact"]}

    m = re.fullmatch(r"prepara (?:las? )?ofertas? (.+)", t)
    if m:
        arg = m.group(1)
        by_id = bool(re.search(r"\bid\b", arg)) or any(n > 8 for n in _nums(arg))
        nums = _nums(arg)
        if not nums:
            return {"intent": "error", "reason": "sin números u IDs"}
        return {"intent": "prepare", "by": "baserow_id" if by_id else "report_number", "values": nums,
                "authorises": "prepare_only", "blocks": ["send", "contact"]}

    m = re.fullmatch(r"prepara (?:el )?contacto " + _ID, t)
    if m:  # P-2: Writer drafts a short outreach note; the user reviews and sends it himself
        return {"intent": "prepare_contact", "baserow_id": int(m.group(1)),
                "authorises": "outreach_draft_only", "blocks": ["send", "contact"]}

    m = re.fullmatch(r"cambios " + _ID + r"\s*:\s*(.+)", t, flags=re.S)
    if m:
        text = raw.split(":", 1)[1].strip()
        wants_variants = bool(re.search(r"opcion|variante|alternativa", t))
        return {"intent": "change", "baserow_id": int(m.group(1)), "text": text, "variants": wants_variants}

    m = re.fullmatch(r"elijo ([ab]) " + _ID, t)
    if m:
        return {"intent": "choose_variant", "variant": m.group(1).upper(), "baserow_id": int(m.group(2))}

    m = re.fullmatch(r"aprobado " + _ID, t)
    if m:
        return {"intent": "approve_documents", "baserow_id": int(m.group(1)), "authorises": "nothing_external"}

    m = re.fullmatch(r"enviada " + _ID + r"(?: (\d{4}-\d{2}-\d{2}))?", t)
    if m:
        return {"intent": "user_reported_sent", "baserow_id": int(m.group(1)), "date": m.group(2)}

    m = re.fullmatch(r"entrevista " + _ID + r"(?: (\d{4}-\d{2}-\d{2}))?", t)
    if m:
        return {"intent": "interview", "baserow_id": int(m.group(1)), "date": m.group(2)}

    m = re.fullmatch(r"resultado " + _ID + r"\s*:\s*(rechazo|oferta|retirada|otro)\b\s*(.*)", t)
    if m:
        return {"intent": "result", "baserow_id": int(m.group(1)), "outcome": m.group(2), "detail": m.group(3)}

    m = re.fullmatch(r"follow-?up " + _ID + r" (si|no)", t)
    if m:
        return {"intent": "followup_decision", "baserow_id": int(m.group(1)), "decision": m.group(2) == "si",
                "contact_by": "user"}

    m = re.fullmatch(r"(aprueba|rechaza) propuesta (p-?\d+)", t)
    if m:
        return {"intent": "proposal_decision", "proposal_id": "P-" + re.sub(r"\D", "", m.group(2)),
                "approved": m.group(1) == "aprueba"}

    if t in {"pausa", "reanuda", "estado"}:
        return {"intent": {"pausa": "pause", "reanuda": "resume", "estado": "status"}[t]}

    m = re.fullmatch(r"cancela (.+)", t)
    if m:
        return {"intent": "cancel", "target": m.group(1)}

    if re.search(r"\b(envia|enviar|manda|mandar|postula|contacta|contactar)\b", t):
        return {"intent": "refused", "reason": "El sistema no envía postulaciones ni contacta a terceros (D-PM-03)."}

    # A long pasted text right after the system asked for an ad (prepare-request -> needs_ad) is that ad,
    # even without "Aviso <ID>" in front (the user, 2026-11-23, pasted the ad text alone).
    ref = pending_ad_request() if len(raw) >= 400 else None
    if ref:
        return {"intent": "ad_supplied", "ref": ref, "file": None, "has_text": True, "inferred": True,
                "why": f"the system asked for the ad of offer {ref} and no ad has been saved since",
                "authorises": "prepare_only", "blocks": ["send", "contact"],
                "next": "bin/hcb ad-save --ref <ref> --text-file <file with the pasted text>, "
                        "then bin/hcb prepare-request --ref <ref>; say in one line it was filed as offer <ref>"}

    return {"intent": "unknown", "needs": "interpretacion_pm_con_confirmacion"}


def pending_ad_request(hours: int = 24) -> str | None:
    """The offer whose ad the system asked for most recently (event prepare_request_needs_ad), if no ad was
    saved for it since and the request is recent. None when there is nothing pending or it is ambiguous."""
    from datetime import datetime, timedelta
    from . import state
    try:
        evs = state._read("events.jsonl")
    except (OSError, ValueError):
        return None
    pending: dict[str, str] = {}
    for e in evs:
        if e.get("kind") == "prepare_request_needs_ad" and e.get("ref"):
            pending[str(e["ref"])] = e.get("at", "")
        elif e.get("kind") == "ad_saved" and e.get("ref"):
            pending.pop(str(e["ref"]), None)
    if not pending:
        return None
    ref, at = max(pending.items(), key=lambda kv: kv[1])
    try:
        when = datetime.fromisoformat(at)
    except ValueError:
        return None
    if datetime.now(when.tzinfo) - when > timedelta(hours=hours):
        return None
    return ref


def resolve_numbers(numbers: list[int], report: dict) -> dict:
    """Resolve 'Prepara las ofertas [n]' against ONE concrete report version (Master §6.4)."""
    nm = {int(k): v for k, v in report["number_map"].items()}
    resolved, errors = [], []
    for n in numbers:
        if n not in nm:
            errors.append(f"número {n} fuera del rango del informe {report['report_id']}")
        else:
            resolved.append({"number": n, "baserow_id": nm[n]})
    return {"report_id": report["report_id"], "resolved": resolved, "errors": errors,
            "execute": not errors}
