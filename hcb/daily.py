"""Daily new-opportunity alert (user decision D-USR-01, 2026-11-13).

Why: applying within 24 hours of publication, and phoning the contact named in the ad on
the same day, improve the user's chances. The Job Hunter runs Monday-Friday at 07:30, 12:30 and 16:30
(D-USR-02, 2026-11-15) and the PM sends ONE short digest per run with offers not announced before,
each with its call suggestion; empty runs send nothing.

Boundaries that do not change: the system never calls, emails or messages anyone. It shows
the number; the user decides and calls himself (D-PM-03). A digest never authorises
preparation; that still needs `Prepara la oferta [ID]`.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from . import rules, state
from .rules import alignment_key
from .targets import excluded_by_title
from .util import config, dump, fold, now_iso, project_path, stable_key

# Australian phone formats seen in ads: mobiles, landlines with area code, 13/1300/1800, +61.
_PHONE = re.compile(
    r"(?<![\d+])(?:"
    r"\+?61[\s-]?\(?0?[2-478]\)?(?:[\s-]?\d){8}"        # +61 4xx xxx xxx / +61 3 6xxx xxxx
    r"|\(?0[2-478]\)?(?:[\s-]?\d){8}"                   # 04xx xxx xxx / (03) 6xxx xxxx
    r"|1[38]00(?:[\s-]?\d){6}"                          # 1300 / 1800
    r"|13(?:[\s-]?\d){4}"                               # 13 xx xx
    r")(?!\d)")
_MASKED = re.compile(r"\b0[2-478]\s?\d{0,4}\s?[xX*]{2,}")
_CONTACT_NAME = re.compile(
    r"(?i:contact|enquiries|questions|call|speak (?:to|with)|reach out to)\b[^.\n]{0,40}?"
    r"\b([A-Z][a-z]+(?: [A-Z][a-z'-]+){1,2})")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def _normalise(num: str) -> str:
    digits = re.sub(r"\D", "", num)
    if digits.startswith("61"):
        digits = "0" + digits[2:]
    return digits


def extract_contacts(ad_text: str) -> dict:
    """Public contact details stated in the ad. Deterministic; nothing is inferred."""
    phones, seen = [], set()
    for m in _PHONE.finditer(ad_text):
        n = _normalise(m.group(0))
        if n not in seen and len(n) in (6, 10):
            seen.add(n)
            phones.append({"raw": m.group(0).strip(), "normalised": n})
    names = []
    for m in _CONTACT_NAME.finditer(ad_text):
        if m.group(1) not in names and not m.group(1).startswith(("Monday", "The ", "Our ")):
            names.append(m.group(1))
    return {"phones": phones, "contact_names": names,
            "emails": sorted(set(_EMAIL.findall(ad_text))),
            "masked_phone": bool(_MASKED.search(ad_text)) and not phones}


def hours_since(posted_at: str | None, now: datetime) -> float | None:
    if not posted_at:
        return None
    dt = datetime.fromisoformat(posted_at)
    if dt.tzinfo is None:  # date-only / naive: treat as start of that day in the system timezone
        dt = dt.replace(tzinfo=now.tzinfo)
    return round((now - dt).total_seconds() / 3600, 1)


def ref_of(o: dict) -> str:
    """What the user types after a digest. The Baserow ID when the record exists; otherwise (dry-run, no live
    writes yet) a short stable code 'o-xxxxxx' from the opportunity ref (RT-13 showed '[None]')."""
    if o.get("baserow_id") not in (None, ""):
        return o["baserow_id"]
    basis = o.get("opportunity_ref") or o.get("canonical_url") or f"{o.get('employer')}|{o.get('title')}"
    return "o-" + stable_key(basis)[:6]


def _review_reason(o: dict) -> str | None:
    """RT-14: say WHY an offer waits for the user (region-only location, or duties from another field)."""
    if o.get("review_reason"):
        return o["review_reason"]
    reasons = []
    if o.get("location_status") == "region_only":
        reasons.append("confirmar localidad")
    if (o.get("target_match") or {}).get("category_hint") == "needs_review":
        reasons.append("revisar funciones")
    return ", ".join(reasons) or None


def notified_ids() -> set:
    """Offers whose digest delivery was CONFIRMED (rows written by mark_delivered carry `channel`). Rows
    without it come from the pre-fix save() of 2026-11-14..16, which marked offers before any send
    (Telegram was off): they were never delivered, so they do not count."""
    return {str(r["baserow_id"]) for r in state._read("notified.jsonl") if r.get("channel")}


def build_digest(snapshot: dict, now: datetime, since_hours: int | None = None,
                 already_notified: set | None = None) -> dict:
    """New opportunities first seen in the window, eligible ones first, each with a call hint.
    `already_notified` (the CLI passes notified_ids()) drops offers a previous digest announced:
    the 24 h window of two daily runs overlaps, and one offer must reach the user only once."""
    already_notified = already_notified or set()
    since_hours = since_hours or config()["daily_alert"]["window_hours"]
    cutoff = now - timedelta(hours=since_hours)
    items = []
    for o in snapshot.get("opportunities", []):
        disc = o.get("discovered_at")
        if not disc or datetime.fromisoformat(disc) < cutoff or o.get("estado") == "Cerrada":
            continue
        if str(ref_of(o)) in already_notified:
            continue
        if o.get("ranking_category") not in config()["daily_alert"]["include_categories"]:
            continue
        if excluded_by_title(o.get("title", "")):        # the user: no Senior roles (2026-11-17)
            continue
        if _discarded_field(o):                          # other profession / duties from another field
            continue
        items.append(_item(o, now))
    fallback = None
    if not items:
        items, fallback = _fallback_items(now, already_notified)
    # One ordering for the digest and the Top 5 (P-4 B): category first, then rules.alignment_key.
    items.sort(key=lambda i: i.pop("_order"))
    out = {"digest_id": f"D-{now.date().isoformat()}", "generated_at": now.isoformat(timespec="seconds"),
           "window_hours": since_hours, "items": items, "message": render_message(items, now, fallback),
           "contact_performed": False, "authorises": "nothing"}
    if items and not fallback and config()["daily_alert"].get("layout") == "top3":
        out["keyboard"] = keyboard_for(items)
    if fallback:
        out["fallback_once"] = fallback
    return out


_ORDER = {"principal": 0, "exploratoria": 1, "pendiente_revision": 2}


def _discarded_field(o: dict) -> bool:
    """Same discard rules as the Baserow registration (registry.kept): another profession in the title, or a
    catalogue title whose duties belong to another field ("revisar funciones")."""
    from .targets import _stem_rx, catalogue
    t = fold(o.get("title", ""))
    if any(_stem_rx(w).search(t) for w in catalogue().get("out_of_field_titles", [])):
        return True
    return "revisar funciones" in (_review_reason(o) or "")


def _fallback_items(now: datetime, already_notified: set) -> tuple[list, dict | None]:
    """One-time rule (the user, 2026-11-17, first unattended day): on `daily_alert.fallback_once.date`, if a
    run finds nothing new and no digest was delivered earlier that day, send the best `top_n` offers already
    found (alignment_key order) instead of silence. Never on any other date; never twice."""
    fb = config()["daily_alert"].get("fallback_once") or {}
    if not fb or str(fb.get("date")) != now.date().isoformat():
        return [], None
    day = f"D-{now.date().isoformat()}"
    for f in (project_path("reports") / "daily").glob(f"{day}*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        if (d.get("delivery") or {}).get("status") == "delivered":
            return [], None                      # something already reached the user today
    src = project_path("state").parent / fb["candidates_file"]
    if not src.exists():
        return [], None
    exclude = {t.lower() for t in fb.get("exclude_titles") or []}
    pool = []
    from .targets import match_title
    for o in json.loads(src.read_text(encoding="utf-8")).get("opportunities", []):
        # re-match against TODAY's catalogue: the user adjusted it after these records were stored
        m = match_title(o.get("title", ""))
        o = {**o, "target_match": {**(o.get("target_match") or {}), **{k: m.get(k) for k in ("group", "family", "catalogue_title", "match")}}}
        if (o.get("estado") == "Cerrada" or str(ref_of(o)) in already_notified or o["title"].lower() in exclude
                or excluded_by_title(o["title"])):
            continue
        if (o.get("closing_date") or "9999-12-31") < now.date().isoformat():
            continue
        if not (o.get("target_match") or {}).get("group"):
            continue
        if "revisar funciones" in (_review_reason(o) or ""):   # duties from another field: never a "best" offer
            continue
        from .targets import catalogue, _stem_rx
        if any(_stem_rx(w).search(fold(o["title"])) for w in catalogue().get("out_of_field_titles", [])):
            continue
        pool.append(o)
    pool.sort(key=alignment_key)
    chosen = [_item(o, now) for o in pool[: int(fb.get("top_n", 3))]]
    # Nothing good enough: still one status line that day, so the user knows the first run worked.
    return chosen, {"date": fb["date"], "count": len(chosen), "source": fb["candidates_file"]}


def _item(o: dict, now: datetime) -> dict:
    cat = o.get("ranking_category")
    contacts = o.get("contacts") or extract_contacts(o.get("ad_text", ""))
    age = hours_since(o.get("posted_at"), now)
    return {
        "_order": (_ORDER.get(cat, 9), *alignment_key(o)),
        "baserow_id": ref_of(o), "opportunity_ref": o.get("opportunity_ref"),
        "employer": o["employer"], "title": o["title"],
        "category": cat, "fit": o.get("fit"), "closing_date": o.get("closing_date"),
        "alignment": {k: (o.get("target_match") or {}).get(k) for k in ("group", "catalogue_title", "match")},
        "employer_url": o.get("canonical_url") or o.get("url"),
        "review_reason": _review_reason(o) if cat == "pendiente_revision" else None,
        "hours_since_posted": age,
        "within_24h_window": age is not None and age <= 24,
        # An ad that forbids direct contact gets no call hint and no researched contacts (Hermes review).
        "call_suggestion": None if o.get("no_approach_clause") else _call_hint(contacts),
        "entry_signal": o.get("entry_signal"), "bridges_to": o.get("bridges_to") or [],
        "contacts": contacts,
        # P-2: people found by Research `contact_research` (max 2) and the ad's approach policy
        "research_contacts": [] if o.get("no_approach_clause") else (o.get("research_contacts") or [])[:2],
        "no_approach_clause": o.get("no_approach_clause"),
    }


def _call_hint(c: dict) -> str | None:
    if c["phones"]:
        who = c["contact_names"][0] if c["contact_names"] else "el contacto del anuncio"
        return f"Llamar hoy a {who}: {c['phones'][0]['raw']}"
    if c["masked_phone"]:
        return "El anuncio tiene un número oculto: ábrelo en el portal para verlo"
    return None


def _contact_line(c: dict) -> str:
    """One digest line per researched contact (P-2 §5). Only public business channels."""
    who = ", ".join(x for x in (c.get("name"), c.get("title")) if x) or "Canal oficial de empleo"
    src = (c.get("source_url") or "").split("/")[2] if "//" in (c.get("source_url") or "") else c.get("source_url")
    conf = "confirmado" if c.get("confidence") == "confirmed" else "inferido"
    via = (c.get("phone_from_ad") and f"tel. {c['phone_from_ad']}") or \
          (c.get("professional_email") and c.get("email_status") == "verified_public_business" and c["professional_email"]) or \
          (c.get("linkedin_url") and "LinkedIn") or c.get("alternative_contact_url") or "sin canal verificado"
    return f"{who} (fuente: {src}, {conf}) · {via}"


def _call_line(i: dict) -> str:
    if i.get("no_approach_clause"):
        return "⛔ El anuncio pide no contactar: postula solo por el portal"
    if i.get("call_suggestion"):
        return "📞 " + i["call_suggestion"]
    rc = (i.get("research_contacts") or [])
    if rc:
        return "👤 " + _contact_line(rc[0])
    return "📞 Sin información de contacto"


def _fit_label(i: dict) -> str:
    al = i.get("alignment") or {}
    if i.get("fit") is not None:
        return f"fit {i['fit']}"
    if al.get("group"):
        return f"Grupo {al['group']} · {al.get('catalogue_title')}"      # P-4 B / D-P10-1: alignment, no A-H in search
    return "revisar funciones"


def _close(i: dict) -> str:
    c = i.get("closing_date")
    return f"cierra {c[8:10]}/{c[5:7]}" if c and len(c) >= 10 else "cierre no indicado"


def split_top3(items: list[dict]) -> tuple[list, list, list]:
    """P-10: Top 3 = first three non-exploratory offers in digest order (category, then alignment_key);
    then the other non-exploratory offers, best to worst; exploratory ones kept apart."""
    main = [i for i in items if i.get("category") != "exploratoria"]
    expl = [i for i in items if i.get("category") == "exploratoria"]
    return main[:3], main[3:], expl


def keyboard_for(items: list[dict]) -> list[list[dict]]:
    """One `Prepare Docs` button per Top 3 offer. callback_data carries the Baserow row id (P-10), never the rank."""
    top, _, _ = split_top3(items)
    return [[{"text": f"📝 Prepare Docs #{n}", "callback_data": f"hcb:prep:{i['baserow_id']}"[:64]}]
            for n, i in enumerate(top, 1)]


def render_top3(items: list[dict], now: datetime) -> str:
    """P-10 daily message (the user's sketch, 2026-11-20): TOP 3 with link and who to call, then the rest."""
    top, rest, expl = split_top3(items)
    L = [f"🏆 TOP 3 — Mejor alineación ({now:%d/%m})"]
    for n, i in enumerate(top, 1):
        L.append(f"\n{n}. {i['title']} – {i['employer']}")
        reason = f" · pendiente: {i['review_reason']}" if i.get("review_reason") else ""
        L.append(f"   {_fit_label(i)} · {_close(i)}{reason}")
        if i.get("employer_url"):
            L.append(f"   🔗 {i['employer_url']}")
        if i.get("bridges_to"):
            tag = " (Strategic Entry)" if i.get("entry_signal") == "Strategic Entry" else ""
            L.append(f"   Te acerca a: {', '.join(i['bridges_to'])}{tag}")
        L.append(f"   {_call_line(i)}")
        L.append(f"   ▶ Botón Prepare Docs #{n} o «Prepara la oferta {i['baserow_id']}»"
                 + (f" · mensaje: «Prepara contacto {i['baserow_id']}»" if i.get("research_contacts") and not i.get("no_approach_clause") else ""))
    if rest:
        L.append("\n📋 OTRAS OFERTAS (de mejor a peor)")
        for n, i in enumerate(rest, len(top) + 1):
            L.append(f"{n}. {i['title']} – {i['employer']} · {_fit_label(i)} · {_close(i)} · ID {i['baserow_id']}"
                     + (f"\n   🔗 {i['employer_url']}" if i.get("employer_url") else ""))
    if expl:
        L.append("\n🔎 EXPLORATORIAS")
        for i in expl:
            L.append(f"• {i['title']} – {i['employer']} · {_fit_label(i)} · {_close(i)} · ID {i['baserow_id']}"
                     + (f"\n   🔗 {i['employer_url']}" if i.get("employer_url") else "")
                     + (f"\n   Te acerca a: {', '.join(i['bridges_to'])}" + (" (Strategic Entry)" if i.get("entry_signal") == "Strategic Entry" else "")
                        if i.get("bridges_to") else ""))
    L.append("\nTop 3: botón Prepare Docs. Cualquier otra: «Prepara la oferta <ID>».")
    L.append("El sistema no llama ni postula: tú decides y contactas.")
    return "\n".join(L)


def render_message(items: list[dict], now: datetime, fallback: dict | None = None) -> str:
    """Spanish, short, one block per offer (PM channel rules)."""
    if items and not fallback and (config()["daily_alert"].get("layout") == "top3"):
        return render_top3(items, now)
    if not items and fallback:
        return (f"Career Buddy ({now:%d/%m}): primera corrida automática OK. Hoy no hay ofertas nuevas, y de lo "
                "ya encontrado ninguna calza bien con tus roles objetivo (sin Senior, Lead, Principal ni Manager, "
                "ni funciones de otra área). Desde mañana, sin novedades no te escribo.")
    if not items:
        return "Hoy no hay ofertas nuevas que cumplan los criterios."
    if fallback:
        lines = [f"Hoy ({now:%d/%m}) no hay ofertas nuevas. Primera corrida automática: "
                 + (f"estas son las {len(items)} mejores" if len(items) > 1 else "esta es la mejor")
                 + " que el sistema ya encontró (por alineación con tus roles objetivo; sin Senior, Lead, Principal ni Manager):"]
    else:
        lines = [f"Ofertas nuevas ({now:%d/%m}): {len(items)}"]
    labels = {"principal": "Ranking", "exploratoria": "Exploratoria", "pendiente_revision": "Pendiente de revisión"}
    for i in items:
        al = i.get("alignment") or {}
        if i["fit"] is not None:
            fit = f"fit {i['fit']}"
        elif al.get("group"):
            fit = f"Grupo {al['group']} ({al.get('catalogue_title')})"   # P-4 B: alignment, A-H only when preparing
        else:
            fit = "revisar funciones"
        age = f"publicada hace {i['hours_since_posted']:.0f} h" if i["hours_since_posted"] is not None else "fecha de publicación no indicada"
        label = labels.get(i['category'], i['category'])
        if i.get("review_reason"):
            label += f" ({i['review_reason']})"
        lines.append(f"\n[{i['baserow_id']}] {i['title']} – {i['employer']}\n"
                     f"{label} · {fit} · cierre {i['closing_date'] or 'no indicado'} · {age}")
        if i.get("bridges_to"):
            tag = " (Strategic Entry)" if i.get("entry_signal") == "Strategic Entry" else ""
            lines.append(f"Te acerca a: {', '.join(i['bridges_to'])}{tag}")
        if i["call_suggestion"]:
            lines.append("📞 " + i["call_suggestion"])
        if i.get("no_approach_clause"):
            lines.append("⛔ El anuncio pide no contactar directamente: solo postula por el portal")
        for c in i.get("research_contacts") or []:
            lines.append("👤 " + _contact_line(c))
        lines.append(f"Para preparar: Prepara la oferta {i['baserow_id']}")
        if i.get("research_contacts"):
            lines.append(f"Para el mensaje: Prepara contacto {i['baserow_id']}")
    lines.append("\nEl sistema no llama ni postula: tú decides y contactas.")
    return "\n".join(lines)


def save(digest: dict) -> str:
    """Write the digest as PENDING delivery. Offers are marked notified only by mark_delivered(), after the
    channel confirmed the send: a failed Telegram send must never hide an offer from the next digest."""
    out = project_path("reports") / "daily"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{digest['digest_id']}.json"
    if path.exists():  # several runs (or retries) on one day: never overwrite, add a counter
        stem = f"{digest['digest_id']}-{digest['generated_at'][11:16].replace(':', '')}"
        path, n = out / f"{stem}.json", 2
        while path.exists():
            path, n = out / f"{stem}-{n}.json", n + 1
    digest["delivery"] = {"status": "pending" if (digest["items"] or digest.get("fallback_once")) else "nothing_to_send"}
    path.write_text(dump(digest), encoding="utf-8")
    state.event("daily_digest", digest_id=digest["digest_id"], items=len(digest["items"]), delivery="pending")
    return str(path)


def send(path, runner=None) -> dict:
    """Send one saved digest to the user's Telegram with `hermes send` (no LLM) and record the outcome.
    Off unless features.telegram_delivery is true. Empty digests are never sent (silent_when_empty)."""
    path = Path(path)
    digest = json.loads(path.read_text(encoding="utf-8"))
    if not config()["features"].get("telegram_delivery"):
        return {"digest": str(path), "status": "not_sent", "reason": "features.telegram_delivery is false"}
    if not digest["items"] and not digest.get("fallback_once"):
        return {"digest": str(path), "status": "nothing_to_send"}
    if (digest.get("delivery") or {}).get("status") == "delivered":
        return {"digest": str(path), "status": "delivered", "already": True}
    if digest.get("keyboard") and (config().get("telegram") or {}).get("buttons") and runner is None:
        from . import telegram_api
        ok, ref, err = telegram_api.send_message(digest["message"], digest["keyboard"])
    else:
        ok, ref, err = hermes_send(digest["message"], runner)
    return mark_delivered(path, "telegram", ref) if ok else mark_delivered(path, "telegram", error=err)


def hermes_send(text: str, runner=None) -> tuple[bool, str | None, str | None]:
    """Send one Telegram message (text; `MEDIA:<path>` lines attach files) with `hermes send`, no LLM.
    Returns (ok, message_id, error). `hermes send` exits 0 even on failure, so only a message_id counts."""
    import subprocess
    import tempfile
    tg = config().get("telegram") or {}
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        body = f.name
    cmd = ["hermes", "-p", tg.get("profile", "career-buddy"), "send", "-t", tg.get("target", "telegram"),
           "--json", "-f", body]
    import sys
    if runner is None and ("unittest" in sys.modules or os.environ.get("HCB_NO_LIVE_WRITES")):
        return False, None, "test run: real Telegram sends are disabled"
    run = runner or (lambda c: subprocess.run(c, capture_output=True, text=True, timeout=180))
    try:
        proc = run(cmd)
    finally:
        Path(body).unlink(missing_ok=True)
    out = (proc.stdout or "").strip()
    start = out.find("{")                     # hermes may print warnings before the JSON object
    try:
        res = json.loads(out[start:]) if start >= 0 else {}
    except ValueError:
        res = {}
    if proc.returncode == 0 and not res.get("error") and res.get("message_id"):
        return True, str(res["message_id"]), None
    return False, None, (res.get("error") or proc.stderr or out or f"exit {proc.returncode}").strip()


def mark_delivered(path, channel: str, message_ref: str | None = None, error: str | None = None) -> dict:
    """Record the outcome of sending one saved digest. Delivered -> its offers are notified (never announced
    again). Failed -> nothing is marked, so the offers come back in the next digest. Idempotent: a digest
    already delivered is not marked twice."""
    path = Path(path)
    digest = json.loads(path.read_text(encoding="utf-8"))
    prev = (digest.get("delivery") or {}).get("status")
    if prev == "delivered":
        return {"digest": str(path), "status": "delivered", "already": True, "marked": 0}
    if error:
        digest["delivery"] = {"status": "failed", "channel": channel, "error": error[:300], "at": now_iso()}
        marked = 0
    else:
        done = notified_ids()
        marked = 0
        for i in digest["items"]:
            if str(i["baserow_id"]) not in done:
                state._append("notified.jsonl", {"baserow_id": i["baserow_id"], "digest_id": digest["digest_id"],
                                                 "channel": channel, "message_ref": message_ref})
                marked += 1
        digest["delivery"] = {"status": "delivered", "channel": channel, "message_ref": message_ref, "at": now_iso()}
    path.write_text(dump(digest), encoding="utf-8")
    state.event("delivery", what="daily_digest", digest_id=digest["digest_id"], channel=channel,
                status=digest["delivery"]["status"], items=len(digest["items"]), marked=marked)
    return {"digest": str(path), "status": digest["delivery"]["status"], "marked": marked}
