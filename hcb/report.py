"""Weekly Report builder (Master §3.12, §6.4, project-manager.md §6.4.7).

Input: a JSON snapshot of opportunities/applications (from Baserow via the adapter, or a
fixture). Output: reports/<report_id>/report.html + report.pdf + report.json with the
frozen number_map that 'Prepara las ofertas [n]' resolves against. Max 3 pages.
Delivery (Gmail TV-07 / Telegram TV-08) is a separate, recorded step.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
from datetime import date
from pathlib import Path

from . import rules, state
from .util import config, dump, now_iso, project_path

def _find_chrome() -> str:
    """macOS Chrome, or Chromium/Chrome on Linux (VPS); HCB_CHROME overrides."""
    import os as _os
    import shutil as _sh
    for c in (_os.environ.get("HCB_CHROME"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              _sh.which("chromium"), _sh.which("chromium-browser"), _sh.which("google-chrome"), _sh.which("google-chrome-stable")):
        if c and Path(c).exists():
            return c
    return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


CHROME = _find_chrome()


def _rows(items, cols):
    if not items:
        return "<p><em>Sin elementos.</em></p>"
    head = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(i.get(c, '') if i.get(c) is not None else ''))}</td>"
                                    for c in cols) + "</tr>" for i in items)
    return f"<table><tr>{head}</tr>{body}</table>"


def title_only_this_week(today: date) -> list[str]:
    from datetime import timedelta
    start = (today - timedelta(days=7)).isoformat()
    out = []
    for e in state._read("seen.jsonl"):
        if e.get("rule") == "T0" and (e.get("decided_at") or "")[:10] >= start:
            t = (e.get("job_key") or "||").split("|")[1]
            if t and t not in out:
                out.append(t)
    return out


def build(snapshot: dict, today: date, report_id: str | None = None, market_synthesis: str = "Sin novedades relevantes") -> dict:
    records = snapshot.get("opportunities", [])
    top = rules.select_top(records)
    expl = rules.select_exploratory(records)
    nm = rules.number_map(top, expl)
    report_id = report_id or f"R-{today.isocalendar()[0]}-W{today.isocalendar()[1]:02d}"
    follow = rules.followups_due(snapshot.get("applications", []), today)
    by_alignment = rules.alignment_basis() and any(r.get("target_match") for r in top)

    def _align(r):
        tm = r.get("target_match") or {}
        s = f"Grupo {tm.get('group')} · {tm.get('catalogue_title')}" if tm.get("group") else ""
        return s + (" · Strategic Entry" if r.get("entry_signal") == "Strategic Entry" else "")
    top_rows = [{"#": i, "ID": r["baserow_id"], "Empresa": r["employer"], "Cargo": r["title"],
                 "Fit": r["fit"] if r.get("fit") is not None else "al preparar", "Alineación": _align(r),
                 "Cierre": r.get("closing_date"), "Razón": r.get("priority_reason", "")} for i, r in enumerate(top, 1)]
    expl_rows = [{"#": i, "ID": r["baserow_id"], "Empresa": r["employer"], "Cargo": r["title"],
                  "Justificación": r["exploratory_justification"]} for i, r in enumerate(expl, 6)]
    decisions = snapshot.get("decisions_required", [])
    by_title = title_only_this_week(today)
    if by_title:   # RT-14b strict boards: cards logged by title alone, never opened (The user can ask for any)
        decisions = decisions + [f"{len(by_title)} anuncios descartados solo por el título esta semana "
                                 f"(p. ej. {', '.join(by_title[:3])}). Pide 'revisa <cargo>' si alguno te interesa."]
    if len(top) < config()["thresholds"]["top_n"]:
        decisions = decisions + [(f"Solo {len(top)} ofertas alineadas con tus roles objetivo; el Top 5 no se rellena."
                                  if by_alignment else
                                  f"Solo {len(top)} ofertas superan el umbral de fit > 50 %; el Top 5 no se rellena.")]
    css = ("body{font-family:Arial,Helvetica,sans-serif;font-size:10.5pt;margin:18mm}h1{font-size:15pt}"
           "h2{font-size:12pt;margin-top:12pt}table{border-collapse:collapse;width:100%;font-size:9pt}"
           "td,th{border:1px solid #999;padding:3px;text-align:left;vertical-align:top}")
    body = (f"<h1>Career Buddy: informe semanal {html.escape(report_id)}</h1>"
            f"<p>Generado {html.escape(now_iso())}. Ranking completo en Baserow.</p>"
            f"<h2>Resumen ejecutivo</h2><p>{html.escape(snapshot.get('executive_summary', ''))}</p>"
            f"<h2>Decisiones requeridas</h2>" + _rows([{"Decisión": d} for d in decisions], ["Decisión"]) +
            ("<h2>Top 5 (alineación con tus roles objetivo)</h2>" + _rows(top_rows, ["#", "ID", "Empresa", "Cargo", "Alineación", "Fit", "Cierre"])
             if by_alignment else
             "<h2>Top 5 (fit &gt; 50 %)</h2>" + _rows(top_rows, ["#", "ID", "Empresa", "Cargo", "Fit", "Cierre", "Razón"])) +
            "<h2>Exploratorias (fuera del ranking)</h2>" + _rows(expl_rows, ["#", "ID", "Empresa", "Cargo", "Justificación"]) +
            f"<h2>Mercado</h2><p>{html.escape(market_synthesis)}</p>"
            "<h2>Postulaciones y follow-ups</h2>" +
            _rows([{"ID": f["baserow_id"], "Días": f["days_since_sent"], "Acción": "Recomendar follow-up (lo hace el usuario)"}
                   for f in follow], ["ID", "Días", "Acción"]) +
            "<h2>Acciones propuestas para el fin de semana</h2>" +
            _rows([{"Acción": a} for a in snapshot.get("proposed_weekend_actions", [])], ["Acción"]) +
            "<p>Para preparar: <b>Prepara las ofertas [números]</b>. Preparar no autoriza enviar.</p>")
    out = project_path("reports") / report_id
    out.mkdir(parents=True, exist_ok=True)
    html_path = out / "report.html"
    html_path.write_text(f"<!doctype html><meta charset='utf-8'><style>{css}</style>{body}", encoding="utf-8")
    pdf = out / "report.pdf"
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                    f"file://{html_path}"], capture_output=True, timeout=120)
    pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes())) if pdf.exists() else None
    report = {"report_id": report_id, "generated_at": now_iso(), "language": "es", "number_map": nm,
              "top5": top_rows, "exploratory": expl_rows, "followups_recommended": follow,
              "page_count": pages, "within_limit": pages is not None and pages <= config()["limits"]["report_pages_max"],
              "files": {"html": str(html_path), "pdf": str(pdf)}, "delivery": None}
    (out / "report.json").write_text(dump(report), encoding="utf-8")
    state.event("report_generated", report_id=report_id, pages=pages, within_limit=report["within_limit"])
    return report


def send(report_id: str, runner=None) -> dict:
    """Send the weekly report PDF to the user's Telegram (hermes send, no LLM) and record it in report.json.
    Gmail stays off (TV-07). Refuses a report over the page limit; never sends twice."""
    from . import daily
    rep = load(report_id)
    path = project_path("reports") / report_id / "report.json"
    if not config()["features"].get("telegram_delivery"):
        return {"report_id": report_id, "status": "not_sent", "reason": "features.telegram_delivery is false"}
    if (rep.get("delivery") or {}).get("status") == "delivered":
        return {"report_id": report_id, "status": "delivered", "already": True}
    if not rep.get("within_limit"):
        return {"report_id": report_id, "status": "not_sent", "reason": f"page_count {rep.get('page_count')} over the limit"}
    n_top, n_exp = len(rep.get("top5") or []), len(rep.get("exploratory") or [])
    import shutil
    import tempfile
    # `MEDIA:` paths stop at the first space and the project folder has spaces: send a copy from a temp dir.
    tmpdir = Path(tempfile.mkdtemp(prefix="hcb-report-"))
    pdf = tmpdir / f"Weekly-Report-{re.sub(r'[^A-Za-z0-9-]+', '-', report_id)}.pdf"
    shutil.copyfile(rep["files"]["pdf"], pdf)
    text = (f"📊 Reporte semanal {report_id}: {n_top} en el Top 5, {n_exp} exploratorias, "
            f"{len(rep.get('followups_recommended') or [])} seguimientos sugeridos.\n"
            # no square brackets: hermes send drops the attachment when the caption has "[...]" (tested 2026-11-19)
            "Para preparar escribe Prepara las ofertas y los números del reporte (por ejemplo 1 y 3). "
            "Preparar no autoriza enviar.\n"
            f"MEDIA:{pdf}")
    try:
        ok, ref, err = daily.hermes_send(text, runner)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    rep["delivery"] = ({"status": "delivered", "channel": "telegram", "message_ref": ref, "at": now_iso()} if ok
                       else {"status": "failed", "channel": "telegram", "error": (err or "")[:300], "at": now_iso()})
    path.write_text(dump(rep), encoding="utf-8")
    state.event("delivery", what="weekly_report", report_id=report_id, status=rep["delivery"]["status"])
    return {"report_id": report_id, **rep["delivery"]}


def load(report_id: str) -> dict:
    return json.loads((project_path("reports") / report_id / "report.json").read_text(encoding="utf-8"))


def latest() -> dict | None:
    reports = sorted(Path(project_path("reports")).glob("*/report.json"), key=lambda p: p.stat().st_mtime)
    return json.loads(reports[-1].read_text(encoding="utf-8")) if reports else None
