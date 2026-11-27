"""Deterministic business rules (Master §3.3-3.14, job-hunter.md §6.7, project-manager.md §4.3).

The LLM extracts and interprets; these functions decide. A-H fit is never computed
here: it comes from the existing evaluator (hcb/ah_adapter.py).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from .util import config


def _threshold() -> Decimal:
    return Decimal(str(config()["thresholds"]["main_ranking_fit_strictly_above"]))


def above_threshold(fit) -> bool:
    """UT-01 / UT-02: strictly greater than 50 %. 50.00 is excluded."""
    return fit is not None and Decimal(str(fit)) > _threshold()


def is_exploratory_eligible(o: dict) -> bool:
    """job-hunter.md §6.7.1: all four conditions."""
    if o.get("entry_signal") == "Dead-End Risk":
        return False
    if not (o.get("exploratory_justification") or "").strip():
        return False
    if o.get("route") == "C" and o.get("entry_signal") != "Strategic Entry":
        return False
    return bool(o.get("entry_signal") == "Strategic Entry" or o.get("employer_tier") == 1
                or o.get("blocked_only_by_seniority_or_equivalence") or (o.get("eoi") and o.get("employer_tier") == 1))


def alignment_basis() -> bool:
    """P-4 option B (AP-8b0ed42a08712e3b6d21afc1): rank by alignment with the user's target roles."""
    return config().get("ranking", {}).get("basis") == "alignment"


_GROUP_ORDER = "ABCDE"


def alignment_key(o: dict) -> tuple:
    """Deterministic order: catalogue group A..E, exact title before contained, Strategic Entry first,
    more target roles bridged first, then the sooner closing date."""
    tm = o.get("target_match") or {}
    g = tm.get("group")
    return (_GROUP_ORDER.index(g) if g and g in _GROUP_ORDER else 9,
            0 if tm.get("match") == "exact" else 1,
            0 if o.get("entry_signal") == "Strategic Entry" else 1,
            -len(o.get("bridges_to") or []),
            o.get("closing_date") or "9999-12-31")


def _classify_by_alignment(o: dict, out) -> dict:
    tm = o["target_match"]
    hint = tm.get("category_hint")
    if hint == "out_of_catalogue" or (tm.get("match") == "none" and hint != "needs_review"):
        return out("A0", "seen_log:out_of_catalogue")          # never shown in the digest (P-4 §4)
    if tm.get("match") == "none":
        # The user, 2026-11-27: an agent's "needs_review" never keeps a title outside the catalogue when the title
        # is another profession, or when nothing ties it to the targets: no aligned word and no duties read.
        from . import targets
        title = o.get("title") or o.get("job_title") or tm.get("title") or ""
        if targets.out_of_field(title) or (not targets.aligned_tokens(title) and not tm.get("bridge_categories")):
            return out("A0", "seen_log:out_of_catalogue")
    if o.get("ah_recommendation") == "DO_NOT_RECOMMEND" and not o.get("ah_override"):
        return out("A1", "baserow", "fuera_de_ranking")        # known knockout (only after a preparation A-H)
    if hint == "needs_review":
        return out("A2", "baserow", "pendiente_revision")
    if hint in ("exploratoria", "exploratoria_if_strategic_entry"):
        if hint == "exploratoria" or o.get("entry_signal") == "Strategic Entry":
            return out("A3", "baserow", "exploratoria")
        return out("A3", "seen_log:generic_admin_without_strategic_entry")
    return out("A4", "baserow", "principal")                    # principal_candidate, groups A-D


def classify(o: dict) -> dict:
    """Classification table C1-C11, applied in order. Returns {rule, destination, ranking_category}.
    With ranking.basis = alignment (P-4 B) and a target_match, C7-C11 are replaced by A0-A4."""
    def out(rule, destination, category=None):
        return {"rule": rule, "destination": destination, "ranking_category": category}

    if not o.get("in_zone", True):
        return out("C1", "seen_log:out_of_scope_zone")
    if o.get("eligibility_flag") == "8579-Fail":
        return out("C2", "seen_log:excluded_eligibility")
    if o.get("work_rights_unmet"):
        return out("C3", "seen_log:excluded_eligibility")
    if o.get("taxonomy_excluded"):
        return out("C4", "seen_log:excluded_false_positive")
    if o.get("mining_function_at_mining_company"):
        return out("C5", "seen_log:excluded_mining")
    if o.get("closed_at_discovery"):
        return out("C6", "seen_log:expired_at_discovery")
    if o.get("eoi"):  # §6.7.2: never A-H evaluated as a vacancy, never main ranking
        if is_exploratory_eligible(o):
            return out("EOI", "baserow", "exploratoria")
        return out("EOI", "seen_log:below_threshold")
    if alignment_basis() and o.get("target_match"):
        r = _classify_by_alignment(o, out)
        # RT-14: an ad that gives only a region ("South", "North West") is never dropped and never ranked
        # as if the locality were known: it waits for the user to confirm the locality.
        if o.get("location_status") == "region_only" and r["ranking_category"] in ("principal", "exploratoria"):
            r = {**out("A2-LOC", "baserow", "pendiente_revision"), "review_reason": "confirmar localidad"}
        elif r["rule"] == "A2":
            r["review_reason"] = "revisar funciones"
        return r
    fit = o.get("fit")
    if o.get("insufficient_data") or fit is None:
        return out("C7", "baserow", "pendiente_revision")  # UT-08: no fit invented
    if above_threshold(fit) and not o.get("mandatory_gap"):
        return out("C8", "baserow", "principal")
    if above_threshold(fit):
        return out("C10", "baserow", "exploratoria" if is_exploratory_eligible(o) else "fuera_de_ranking")
    if is_exploratory_eligible(o):
        return out("C11", "baserow", "exploratoria")
    return out("C11", "seen_log:below_threshold")


def _closing_key(o):
    return o.get("closing_date") or "9999-12-31"


def select_top(records: list[dict], n: int | None = None) -> list[dict]:
    """UT-03: Top N from main ranking only, fit descending; never padded."""
    n = n or config()["thresholds"]["top_n"]
    if alignment_basis() and any(r.get("target_match") for r in records):
        main = [r for r in records if r.get("ranking_category") == "principal" and r.get("estado") != "Cerrada"
                and r.get("target_match")]
        main.sort(key=alignment_key)
        return main[:n]          # never padded: fewer than 5 aligned offers -> fewer than 5
    main = [r for r in records if r.get("ranking_category") == "principal" and above_threshold(r.get("fit"))
            and r.get("estado") != "Cerrada"]
    main.sort(key=lambda r: (-Decimal(str(r["fit"])), _closing_key(r)))
    return main[:n]


def select_exploratory(records: list[dict], n: int | None = None) -> list[dict]:
    """UT-04: separate list, each item must carry a one-line justification."""
    n = n or config()["thresholds"]["exploratory_n"]
    expl = [r for r in records if r.get("ranking_category") == "exploratoria" and r.get("estado") != "Cerrada"
            and (r.get("exploratory_justification") or "").strip()
            and "\n" not in r["exploratory_justification"].strip()]
    expl.sort(key=lambda r: (alignment_key(r) if alignment_basis() and r.get("target_match") else (),
                             0 if r.get("employer_tier") == 1 else 1, _closing_key(r)))
    return expl[:n]


def number_map(top: list[dict], exploratory: list[dict]) -> dict:
    """Stable numbers inside one report: 1-5 top, 6-8 exploratory (project-manager.md §6.4.7)."""
    nm = {}
    for i, r in enumerate(top, 1):
        nm[i] = r["baserow_id"]
    for i, r in enumerate(exploratory, 6):
        nm[i] = r["baserow_id"]
    return nm


def followups_due(applications: list[dict], today: date) -> list[dict]:
    """UT-15: recommend (never send) after 10 days without response."""
    days = config()["thresholds"]["followup_days_without_response"]
    due = []
    for a in applications:
        if a.get("state") != "enviada" or not a.get("sent_date") or a.get("response_received"):
            continue
        elapsed = (today - date.fromisoformat(a["sent_date"])).days
        if elapsed >= days:
            due.append({**a, "days_since_sent": elapsed, "action": "recommend_followup", "contact_performed": False})
    return due


def expire(record: dict, today: date) -> dict:
    """UT-09: an expired offer becomes Cerrada; it is never deleted."""
    closing = record.get("closing_date")
    if closing and date.fromisoformat(closing[:10]) < today:
        return {**record, "estado": "Cerrada", "deleted": False}
    return record


# Application lifecycle (Master §8.3). Sending needs a separate user action.
APP_TRANSITIONS = {
    "preparacion_autorizada": {"documentos_en_preparacion"},
    "documentos_en_preparacion": {"revision_recruiter"},
    "revision_recruiter": {"revision_recruiter", "lista_revision_humana"},
    "lista_revision_humana": {"cambios_solicitados", "documentos_aprobados"},
    "cambios_solicitados": {"documentos_en_preparacion"},
    "documentos_aprobados": {"lista_para_envio"},
    "lista_para_envio": {"enviada"},
    "enviada": {"en_espera", "entrevista", "rechazo", "retirada", "otro"},
    "en_espera": {"entrevista", "rechazo", "retirada", "otro"},
}


def can_transition(current: str, target: str, approvals: set[str], package: dict | None = None) -> tuple[bool, str]:
    """UT-10: preparing never authorises sending. `approvals` holds the approval actions on record."""
    if target not in APP_TRANSITIONS.get(current, set()):
        return False, f"transition {current} -> {target} not allowed"
    if target == "lista_para_envio":
        if "approve_documents" not in approvals:
            return False, "requires the user's 'Aprobado [ID]'"
        if package and package.get("send_readiness") == "not_fit_to_send":
            return False, "Recruiter marked the package not_fit_to_send (D-RC-01)"
    if target == "enviada" and "user_reported_sent" not in approvals:
        return False, "only the user sends; record requires 'Enviada [ID]' (D-PM-03)"
    return True, "ok"


def alert_candidate(o: dict, next_report_monday: date) -> bool:
    """D-PM-05: exceptional fit >= 80 and closing before the Monday after the next report."""
    fit_min = config()["thresholds"]["alert_exceptional_fit_min"]
    closing = o.get("closing_date")
    return (o.get("ranking_category") == "principal" and o.get("fit") is not None
            and Decimal(str(o["fit"])) >= fit_min and bool(closing)
            and date.fromisoformat(closing[:10]) <= next_report_monday)


def next_report_monday(today: date) -> date:
    days_to_sat = (5 - today.weekday()) % 7
    return today + timedelta(days=days_to_sat + 2)
