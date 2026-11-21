"""Status page and pipeline board (P-13). No LLM, read-only.

`bin/hcb dashboard` writes one static HTML file to <private>/reports/dashboard/index.html from:
- Baserow Applications (read-only list; Baserow stays the only place where rows change),
- the Hermes cron job list of the career-buddy profile (last run, status, next run),
- the logs in <private>/state (events, source reads, discovery runs, sweeps),
- config/sources.yaml and config/employers.yaml.
The page holds personal data: it lives in the private zone, uses inline CSS only and loads nothing from the web.
Any missing input renders as "unknown"; building the page never raises into the caller.
"""
from __future__ import annotations

import html
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from . import state, util

BOARD = ["Discovered", "Shortlisted", "Waiting Documents", "Preparing", "Ready for Review", "Applied", "Interview"]
FINAL = ["Rejected", "Withdrawn", "Closed"]
STATUS_ES = {"Discovered": "Nueva", "Shortlisted": "Seleccionada", "Waiting Documents": "Esperando datos",
             "Preparing": "Preparando", "Ready for Review": "Lista para revisar", "Applied": "Enviada",
             "Interview": "Entrevista", "Rejected": "Rechazada", "Withdrawn": "Retirada", "Closed": "Cerrada"}
JOB_ES = {"jh-weekday-search-and-digest": "Búsqueda (lun-vie 07:30, 12:30, 16:30)",
          "friday-market-and-maintenance": "Revisión del viernes 18:00", "saturday-report": "Informe del sábado 08:00",
          "daily-backup": "Respaldo diario 03:00"}
LATE_AFTER = timedelta(hours=1)


# ---------------------------------------------------------------- inputs (each one may fail -> None)
def _val(v):
    return v.get("value") if isinstance(v, dict) else v


def load_rows():
    try:
        from . import baserow
        return [{k: _val(v) for k, v in r.items()} for r in baserow.list_rows()]
    except Exception:
        return None


def load_jobs():
    prof = (util.config().get("telegram") or {}).get("profile", "career-buddy")
    # Inside a Hermes session HOME and HERMES_HOME may point at the profile itself, so try each layout.
    cands = []
    if os.environ.get("HERMES_HOME"):
        h = Path(os.environ["HERMES_HOME"])
        cands += [h / "profiles" / prof / "cron" / "jobs.json", h / "cron" / "jobs.json"]
    for base in (os.environ.get("HERMES_REAL_HOME"), str(Path.home())):
        if base:
            cands.append(Path(base) / ".hermes" / "profiles" / prof / "cron" / "jobs.json")
    for p in cands:
        try:
            d = json.loads(p.read_text())
            return d if isinstance(d, list) else d.get("jobs", [])
        except Exception:
            continue
    return None


def _dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def _d(s):
    try:
        return date.fromisoformat(str(s)[:10]) if s else None
    except ValueError:
        return None


def _sweeps(since: datetime) -> list[dict]:
    out = []
    d = util.project_path("state") / "sweeps"
    for f in sorted(d.glob("sweep-*.json")) if d.exists() else []:
        try:
            s = json.loads(f.read_text())
        except Exception:
            continue
        at = _dt(s.get("simulated_now") or s.get("at"))
        if at and at >= since:
            out.append(s)
    return out


# ---------------------------------------------------------------- model
def build(now: datetime, rows=None, jobs=None, use_live: bool = True) -> dict:
    rows = rows if rows is not None else (load_rows() if use_live else None)
    jobs = jobs if jobs is not None else (load_jobs() if use_live else None)
    today = now.date()
    week_start = now - timedelta(days=7)
    m = {"generated": now.isoformat(timespec="minutes"), "baserow_ok": rows is not None}

    # today / board
    active = [r for r in rows or [] if (r.get("Status") or "Discovered") not in FINAL]
    m["ready"] = [r for r in active if r.get("Status") == "Ready for Review"]
    m["closing"] = sorted([r for r in active if _d(r.get("Closing Date")) and 0 <= (_d(r["Closing Date"]) - today).days <= 7
                           and r.get("Status") not in ("Applied", "Interview")], key=lambda r: r["Closing Date"])
    m["followups"] = [r for r in active if r.get("Status") in ("Applied", "Interview")
                      and _d(r.get("Next Follow Up")) and _d(r["Next Follow Up"]) <= today]
    cols = defaultdict(list)
    for r in rows or []:
        cols[r.get("Status") or "Discovered"].append(r)
    for c in cols.values():
        c.sort(key=lambda r: (r.get("Closing Date") or "9999", r.get("Job Title") or ""))
    m["board"] = {s: cols.get(s, []) for s in BOARD}
    m["final_counts"] = {s: len(cols.get(s, [])) for s in FINAL}

    # health: scheduled jobs
    hj = []
    for j in jobs or []:
        if not j.get("next_run_at") and not str(j.get("name", "")).startswith(tuple(JOB_ES)):
            continue                                   # one-off reminders that already ran
        nxt, last = _dt(j.get("next_run_at")), _dt(j.get("last_run_at"))
        late = bool(nxt and now - nxt > LATE_AFTER)
        status = "atrasada" if late else ("ok" if j.get("last_status") == "ok" else (j.get("last_status") or "sin datos"))
        hj.append({"name": JOB_ES.get(j.get("name"), j.get("name")), "last": last, "next": nxt, "status": status})
    m["jobs"] = hj if jobs is not None else None
    ev = state._read("events.jsonl")
    backups = [e for e in ev if e.get("kind") == "backup"]
    m["backup"] = backups[-1] if backups else None
    m["backup_age_h"] = round((now - _dt(m["backup"]["at"])).total_seconds() / 3600, 1) if m["backup"] else None
    deliveries = [e for e in ev if e.get("kind") in ("delivery", "daily_digest") and (_dt(e.get("at")) or now) >= week_start]
    m["deliveries"] = deliveries[-6:]
    m["problems"] = [e for e in ev if e.get("kind") in ("error", "security_event", "engine_exception")
                     and (_dt(e.get("at")) or now) >= week_start][-8:]

    # coverage
    from . import sources as _src
    reg = _src.registry()
    reads = defaultdict(list)
    for r in state._read("source-reads.jsonl"):
        reads[r.get("source")].append(r)
    disc = defaultdict(list)
    for r in state._read("discovery-runs.jsonl"):
        disc[r.get("source")].append(r)
    sweeps = _sweeps(week_start)
    cards_week = Counter()
    for s in sweeps:
        for p in s.get("per_source", []):
            cards_week[p.get("source")] += int(p.get("cards") or 0)
        for p in (s.get("discovery") or {}).get("per_source", []) or []:
            cards_week[p.get("source")] += int(p.get("job_urls") or 0)
    cov = []
    for s in reg:
        if not s.get("enabled"):
            continue
        hist = reads[s["id"]] if s["mode"] == "page_read" else disc[s["id"]]
        last = hist[-1] if hist else None
        fails = 0
        for r in reversed(hist):
            ok = r.get("ok") if s["mode"] == "page_read" else not r.get("error")
            if ok:
                break
            fails += 1
        cov.append({"id": s["id"], "name": s["name"], "mode": s["mode"], "last": _dt((last or {}).get("read_at") or (last or {}).get("at")),
                    "ok": None if not last else (last.get("ok") if s["mode"] == "page_read" else not last.get("error")),
                    "fails": fails, "week": cards_week.get(s["id"], 0)})
    m["coverage"] = sorted(cov, key=lambda c: (c["mode"], -c["fails"], c["name"]))
    try:
        emp = util.load_yaml(util.ROOT / "config" / "employers.yaml").get("employers", [])
        m["employers"] = Counter(ch for e in emp for ch in (e.get("channel") or [])[:1])
    except Exception:
        m["employers"] = Counter()

    # week funnel
    f = {"cards": 0, "out_of_zone": 0, "logged_by_title": 0, "shortlisted": 0}
    for s in sweeps:
        for p in s.get("per_source", []) + list(((s.get("discovery") or {}).get("per_source") or [])):
            f["cards"] += int(p.get("cards") or p.get("job_urls") or 0)
            for k in ("out_of_zone", "logged_by_title", "shortlisted"):
                f[k] += int(p.get(k) or 0)
    new_rows = [r for r in rows or [] if _d(r.get("Discovered")) and _d(r["Discovered"]) >= week_start.date()]
    m["funnel"] = [("Ofertas vistas", f["cards"]), ("En zona", max(f["cards"] - f["out_of_zone"], 0)),
                   ("Pasan el filtro de cargo", f["shortlisted"]), ("Registradas en Baserow", len(new_rows)),
                   ("En preparación o listas", sum(1 for r in rows or [] if r.get("Status") in ("Preparing", "Ready for Review"))),
                   ("Enviadas esta semana", sum(1 for r in rows or [] if _d(r.get("Date applied")) and _d(r["Date applied"]) >= week_start.date()))]
    m["sweeps_week"] = len(sweeps)
    return m


# ---------------------------------------------------------------- render
def _e(x) -> str:
    return html.escape("" if x is None else str(x))


def _when(d) -> str:
    return d.strftime("%a %d %b %H:%M") if isinstance(d, datetime) else "sin datos"


def _card(r: dict, today: date) -> str:
    cd = _d(r.get("Closing Date"))
    days = (cd - today).days if cd else None
    cls = "card urgent" if days is not None and 0 <= days <= 3 else "card"
    close = f"cierra {cd:%d %b}" + (f" ({days} d)" if days is not None and days >= 0 else " (vencida)") if cd else "sin fecha de cierre"
    url = r.get("Job URL") or ""
    link = f'<a href="{_e(url)}" rel="noreferrer noopener" target="_blank">aviso</a>' if url.startswith("https://") else ""
    grp = r.get("Alignment Group")
    return (f'<div class="{cls}"><div class="t">{_e(r.get("Job Title"))}</div>'
            f'<div class="c">{_e(r.get("Company"))} · {_e(r.get("Location"))}</div>'
            f'<div class="m">{_e(close)}{" · grupo " + _e(grp) if grp and grp != "none" else ""}</div>'
            f'<div class="m">ID {_e(r.get("id"))} {link}</div></div>')


def _list(rows, today, empty) -> str:
    if not rows:
        return f'<p class="muted">{_e(empty)}</p>'
    return '<div class="cards">' + "".join(_card(r, today) for r in rows) + "</div>"


CSS = """
:root{--bg:#f6f7f9;--panel:#fff;--ink:#1d232b;--muted:#68717d;--line:#e1e5ea;--ok:#1f8a4c;--bad:#c0392b;--warn:#b7791f;--accent:#2b6cb0}
@media (prefers-color-scheme: dark){:root{--bg:#111418;--panel:#1a1f25;--ink:#e6e9ed;--muted:#97a0ab;--line:#2a3038;--ok:#4cc38a;--bad:#ff6b5e;--warn:#e0a84a;--accent:#6aa9f0}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
header{padding:20px 16px 8px;max-width:1280px;margin:auto}h1{font-size:22px;margin:0}h2{font-size:17px;margin:0 0 10px}
.sub{color:var(--muted);font-size:13px}main{max-width:1280px;margin:auto;padding:8px 16px 40px;display:grid;grid-template-columns:minmax(0,1fr);gap:16px}
section{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;min-width:0}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:16px}.grid3>*{min-width:0}
td{overflow-wrap:anywhere}h3{font-size:15px;margin:4px 0 8px}
.board{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(210px,1fr);gap:10px;overflow-x:auto;padding-bottom:6px}
.col{background:var(--bg);border-radius:8px;padding:8px;min-height:80px}.col h3{font-size:13px;margin:2px 4px 8px;color:var(--muted)}
.cards{display:grid;gap:8px}.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.card.urgent{border-left:4px solid var(--bad)}.t{font-weight:600}.c,.m{font-size:13px;color:var(--muted)}
a{color:var(--accent)}table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--muted);font-weight:500}.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}.muted{color:var(--muted)}
.funnel td:last-child{text-align:right;font-variant-numeric:tabular-nums}.pill{display:inline-block;padding:1px 8px;border-radius:99px;border:1px solid var(--line);font-size:12px;margin:2px}
"""


def _what(e: dict) -> str:
    if e.get("kind") == "daily_digest":
        return f"Resumen diario ({e.get('items', 0)} ofertas)"
    return {"weekly_report": "Informe semanal"}.get(e.get("what"), e.get("what") or e.get("kind"))


def _delivery_status(e: dict) -> str:
    if e.get("kind") == "daily_digest" and str(e.get("items")) in ("0", "None"):
        return "sin novedades: no se envía"
    s = e.get("status") or e.get("delivery")
    return {"delivered": "entregado", "pending": "pendiente", "failed": "falló"}.get(s, s)


def render(m: dict, now: datetime) -> str:
    today = now.date()
    h = [f"<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; img-src 'none'\">"
         f"<title>Career Buddy · Estado</title><style>{CSS}</style></head><body>"
         f"<header><h1>Hermes Career Buddy · Estado</h1><div class='sub'>Actualizado {_e(_when(now))} · "
         f"{'Baserow conectado' if m['baserow_ok'] else '<span class=bad>Baserow no responde: tablero sin datos</span>'} · "
         f"solo lectura: los cambios se hacen en Baserow o por Telegram</div></header><main>"]
    # today
    h.append("<section><h2>Hoy: lo que espera tu decisión</h2><div class='grid3'>")
    h.append("<div><h3>Documentos listos para revisar</h3>" + _list(m["ready"], today, "Nada por revisar.")
             + "<p class='muted'>Revisa el paquete; el envío lo haces tú. Luego «Enviada &lt;ID&gt;».</p></div>")
    h.append("<div><h3>Cierran en 7 días</h3>" + _list(m["closing"], today, "Ninguna oferta abierta cierra esta semana.")
             + "<p class='muted'>Para preparar: botón Prepare Docs o «Prepara la oferta &lt;ID&gt;».</p></div>")
    h.append("<div><h3>Seguimientos para hoy</h3>" + _list(m["followups"], today, "Sin seguimientos pendientes.")
             + "</div></div></section>")
    # board
    h.append("<section><h2>Postulaciones</h2><div class='board'>")
    for s, rs in m["board"].items():
        h.append(f"<div class='col'><h3>{_e(STATUS_ES[s])} · {len(rs)}</h3><div class='cards'>"
                 + "".join(_card(r, today) for r in rs) + "</div></div>")
    h.append("</div><p class='muted'>" + " · ".join(f"{_e(STATUS_ES[k])}: {v}" for k, v in m["final_counts"].items()) + "</p></section>")
    # health
    h.append("<section><h2>Salud del sistema</h2><div class='grid3'><div><h3>Tareas programadas</h3>")
    if m["jobs"] is None:
        h.append("<p class='bad'>No se pudo leer la lista de tareas de Hermes.</p>")
    else:
        h.append("<table><tr><th>Tarea</th><th>Última</th><th>Próxima</th></tr>")
        for j in m["jobs"]:
            cls = "ok" if j["status"] == "ok" else "bad"
            h.append(f"<tr><td>{_e(j['name'])}</td><td class='{cls}'>{_e(_when(j['last']))} · {_e(j['status'])}</td><td>{_e(_when(j['next']))}</td></tr>")
        h.append("</table>")
    b = m["backup"]
    age = m["backup_age_h"]
    bcls = "ok" if b and str(b.get("verified")) in ("True", "true") and age is not None and age < 30 else "bad"
    h.append(f"</div><div><h3>Respaldo</h3><p class='{bcls}'>"
             + (f"Último: {_e(b.get('archive'))}, hace {age} h, verificado: {_e(b.get('verified'))}" if b else "Sin respaldos registrados")
             + "</p><h3>Entregas esta semana</h3>")
    if m["deliveries"]:
        h.append("<table>" + "".join(f"<tr><td>{_e(str(e.get('at'))[:16].replace('T', ' '))}</td><td>{_e(_what(e))}</td>"
                                     f"<td>{_e(_delivery_status(e))}</td></tr>" for e in m["deliveries"]) + "</table>")
    else:
        h.append("<p class='muted'>Sin entregas registradas.</p>")
    h.append("</div><div><h3>Problemas (7 días)</h3>")
    if m["problems"]:
        h.append("<table>" + "".join(f"<tr><td>{_e(str(e.get('at'))[:10])}</td><td class='warn'>{_e(e.get('process') or e.get('kind'))}: "
                                     f"{_e(str(e.get('message') or e.get('detail') or '')[:120])}</td></tr>" for e in m["problems"]) + "</table>")
    else:
        h.append("<p class='ok'>Ninguno.</p>")
    h.append("</div></div></section>")
    # coverage
    h.append(f"<section><h2>Cobertura</h2><p class='muted'>{m['sweeps_week']} búsquedas en 7 días. Empleadores por canal: "
             + " ".join(f"<span class='pill'>{_e(k)}: {v}</span>" for k, v in sorted(m["employers"].items()))
             + "</p><table><tr><th>Fuente</th><th>Modo</th><th>Última lectura</th><th>Ofertas (7 d)</th></tr>")
    for c in m["coverage"]:
        st = "sin lecturas" if c["ok"] is None else ("ok" if c["ok"] else "falló")
        cls = "muted" if c["ok"] is None else ("ok" if c["ok"] else "bad")
        if c["fails"] >= 3:
            st, cls = f"falla {c['fails']} veces seguidas", "bad"
        mode = "lectura directa" if c["mode"] == "page_read" else "búsqueda web"
        h.append(f"<tr><td>{_e(c['name'])}</td><td class='muted'>{mode}</td><td class='{cls}'>{_e(_when(c['last']))} · {_e(st)}</td><td>{c['week']}</td></tr>")
    h.append("</table></section>")
    # funnel
    h.append("<section><h2>Embudo de los últimos 7 días</h2><table class='funnel'>"
             + "".join(f"<tr><td>{_e(k)}</td><td>{v}</td></tr>" for k, v in m["funnel"]) + "</table></section>")
    h.append("</main></body></html>")
    return "".join(h)


def summary(m: dict) -> str:
    bad = [c["name"] for c in m["coverage"] if c["fails"] >= 3]
    late = [j["name"] for j in m["jobs"] or [] if j["status"] != "ok"]
    lines = [f"📋 Por revisar: {len(m['ready'])} · cierran en 7 días: {len(m['closing'])} · seguimientos hoy: {len(m['followups'])}",
             "🗂 Postulaciones activas: " + ", ".join(f"{STATUS_ES[s]} {len(r)}" for s, r in m["board"].items() if r),
             "⚙️ Tareas: " + ("todas OK" if m["jobs"] is not None and not late else ("sin datos" if m["jobs"] is None else "revisar " + ", ".join(late))),
             f"💾 Respaldo: hace {m['backup_age_h']} h" if m["backup_age_h"] is not None else "💾 Respaldo: sin datos",
             "📡 Fuentes con fallas: " + (", ".join(bad) if bad else "ninguna")]
    if not m["baserow_ok"]:
        lines.insert(0, "⚠️ Baserow no responde")
    return "\n".join(lines)


def write(now: datetime | None = None, **kw) -> dict:
    from zoneinfo import ZoneInfo
    now = now or datetime.now(ZoneInfo(util.config()["timezone"]))
    m = build(now, **kw)
    out_dir = util.project_path("reports") / "dashboard"
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    path = out_dir / "index.html"
    fd, tmp = tempfile.mkstemp(dir=out_dir, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(render(m, now))
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    return {"ok": True, "file": str(path), "baserow_ok": m["baserow_ok"], "summary": summary(m)}


def refresh_quietly() -> None:
    """Called at the end of sweep / daily-send / report-send / backup; never breaks them."""
    import sys
    if "unittest" in sys.modules:
        return
    try:
        write()
    except Exception as exc:   # noqa: BLE001
        try:
            state.event("dashboard_failed", error=str(exc)[:200])
        except Exception:
            pass
