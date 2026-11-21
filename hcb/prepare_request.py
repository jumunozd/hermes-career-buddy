"""P-10 `Prepare Docs` button: the same instruction as «Prepara la oferta <ID>», delivered by a button.

Idempotent per offer: a second tap (or a tap after the user already typed the command) starts nothing new.
Marks the Baserow row `Preparing` (create/update only, never delete) and returns the exact instruction the
Project Manager receives. It authorises preparation only; it never authorises sending or contacting anyone.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import baserow, state


def request(ref: str, user_id: str = "", writer=None, live: bool = True) -> dict:
    ref = str(ref).strip()
    if not re.fullmatch(r"\d{1,9}|o-[0-9a-f]{6}", ref):
        return {"status": "refused", "reason": f"invalid offer reference {ref!r}"}
    if ref == "o-000000":                  # reserved test button: proves the tap path, starts nothing
        state.event("prepare_request_test", user=user_id or None)
        return {"status": "test", "ref": ref,
                "confirmation": "📝 PRUEBA: así se ve la confirmación cuando aceptas preparar documentos.\n"
                                "En una oferta real dirá: «Preparación de documentos iniciada: <cargo> – <empresa> (ID n). "
                                "Te aviso cuando estén listos.» Esta prueba no inició nada."}
    if not known(ref):
        state.event("prepare_request_refused", ref=ref, user=user_id or None, reason="unknown offer")
        return {"status": "refused", "reason": f"offer {ref} not found in Baserow or in any sent digest"}
    key = f"prepare-request:{ref}"
    done = state.ledger_get(key)
    if done and done["status"] == "applied":
        t, e = describe(ref)
        return {"status": "already_requested", "ref": ref, "since": done.get("at"),
                "confirmation": f"ℹ️ {t or 'Esa oferta'}{(' – ' + e) if e else ''} (ID {ref}) ya estaba en preparación: no se inició otra."}
    instruction = f"Prepara la oferta {ref}"
    state.ledger_put(key, "prepare_request", ref, "applied")
    state.event("prepare_request", ref=ref, source="telegram_button", user=user_id or None,
                authorises="prepare_only", blocks=["send", "contact"])
    status_written = None
    if ref.isdigit():
        writer = writer or baserow.write
        try:
            r = writer("update", {"Status": "Preparing"}, f"prepare-request-status:{ref}", row_id=int(ref),
                       live=live, task_id="prepare-request")
            status_written = bool(r.get("verified")) if r.get("write_performed") else r.get("mode", r.get("skipped"))
        except Exception as exc:  # the request still stands; the PM records the state when it prepares
            status_written = f"error: {type(exc).__name__}"
    t, e = describe(ref)
    return {"status": "started", "ref": ref, "instruction": instruction, "baserow_status": status_written,
            "title": t, "employer": e,
            "confirmation": f"📝 Preparación de documentos iniciada: {t or 'oferta'}{(' – ' + e) if e else ''} (ID {ref}).\n"
                            "El Writer arma el CV y la carta y el Recruiter los revisa. Te aviso cuando estén listos.\n"
                            "Esto solo prepara: el envío lo haces tú."}


def known(ref: str, rows=None, digest_dir=None) -> bool:
    """The offer must exist: a Baserow row id, or an `o-xxxxxx` code that appeared in a digest that was sent.
    (2026-11-20: a button on a stray test message carried an invented code.)"""
    import json
    from .util import project_path
    if ref.isdigit():
        try:
            rows = rows if rows is not None else baserow.list_rows()
        except Exception:
            return True            # Baserow down: let the PM decide (it reads Baserow again)
        return any(str(r.get("id")) == ref for r in rows)
    d = digest_dir or (project_path("reports") / "daily")
    for f in Path(d).glob("D-*.json"):
        try:
            dg = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if (dg.get("delivery") or {}).get("status") == "delivered" and any(str(i.get("baserow_id")) == ref for i in dg.get("items", [])):
            return True
    return False


def describe(ref: str) -> tuple[str | None, str | None]:
    """Title and employer of the offer, from Baserow (row id) or from the latest sent digest (o-code)."""
    import json
    from .util import project_path
    try:
        if ref.isdigit():
            r = baserow.get_row(int(ref))
            return r.get("Job Title"), r.get("Company")
        for f in sorted((project_path("reports") / "daily").glob("D-*.json"), reverse=True):
            for i in json.loads(f.read_text(encoding="utf-8")).get("items", []):
                if str(i.get("baserow_id")) == ref:
                    return i.get("title"), i.get("employer")
    except Exception:
        pass
    return None, None

