"""Deterministic Recruiter verdict (recruiter.md §7.3) and output-language guard (§9.2).

The LLM classifies requirements and claims; this module decides the verdict from
those classifications so the same inputs always give the same verdict.
"""
from __future__ import annotations

import re

from .util import config

INTEGRITY_DEFECTS = {"overstated", "unsupported", "contradicted"}
BANNED_VERDICT_LANGUAGE = re.compile(
    r"(\d+\s*%|\b\d+\s*(de|of|/)\s*10\b|alta probabilidad|baja probabilidad|\bchance\b|guarantee|"
    r"likely to be hired|probabilidad de (exito|éxito))", re.I)


def gates(review: dict, round_no: int, max_potential: int | None = None) -> dict:
    if max_potential is None:
        max_potential = config()["limits"]["r3_max_essential_gaps_accepted_by_potential"]
    claims = review.get("claims", [])
    reqs = review.get("requirements_assessment", [])
    docs = review.get("document_compliance", [])
    strategic = round_no == 3

    g1 = not any(c.get("claim_status") in INTEGRITY_DEFECTS for c in claims)
    g2 = all(d.get("present") and d.get("format_ok", True) and d.get("limits", {}).get("ok", True)
             and all(c.get("addressed") for c in d.get("criteria_addressed", []))
             and not d.get("unrequested_document") for d in docs)
    g3 = all(r.get("evidence_status") == "met" for r in reqs if r.get("category") == "legal_gate") \
        and review.get("eligibility_flag") != "8579-Fail"
    essential = [r for r in reqs if r.get("category") == "essential"]
    unmet = [r for r in essential if r.get("evidence_status") not in ("met", "transferable")]
    if strategic:
        accepted = [r for r in unmet if r.get("potential_acceptance") and r.get("evidence_status") in ("partial", "absent")]
        g4 = len(unmet) - len(accepted) == 0 and len(accepted) <= max_potential
    else:
        g4 = not unmet
    g5 = not any(q.get("blocking") and q.get("rating") == "fails" for q in review.get("quality_assessment", []))
    result = {"G1_integrity": g1, "G2_documents": g2, "G3_legal": g3, "G4_essential": g4,
              "G5_blocking_quality": g5}
    passed = all(result.values())
    return {"gates": {k: "pass" if v else "fail" for k, v in result.items()},
            "verdict": "Pasa a entrevista" if passed else "No pasa a entrevista",
            "verdict_basis": "strategic" if strategic else "strict",
            "send_readiness": "not_fit_to_send" if not g1 else "ready_for_human_review"}


def check_review(review: dict, round_no: int) -> list[str]:
    """Contract + determinism checks on a Review Result produced by the Recruiter subagent."""
    problems = []
    if round_no > config()["limits"]["recruiter_rounds_max"]:
        problems.append("round limit exceeded (max 3)")
    expected = gates(review, round_no)
    if review.get("verdict") != expected["verdict"]:
        problems.append(f"verdict {review.get('verdict')!r} inconsistent with gates -> {expected['verdict']!r}")
    if review.get("send_readiness") and review["send_readiness"] != expected["send_readiness"]:
        problems.append("send_readiness inconsistent with G1 (D-RC-01)")
    dims = [str(q.get("dimension", "")) for q in review.get("quality_assessment", [])]
    if not any(d.upper().startswith("Q10") for d in dims):
        problems.append("quality_assessment must rate Q10 (natural and authentic language)")
    if not any(d.upper().startswith("Q11") for d in dims):
        problems.append("quality_assessment must rate Q11 (positioning: Industrial Engineer, AI weight per role)")
    text = " ".join(str(r.get("reason", "")) for r in review.get("principal_reasons", []))
    if BANNED_VERDICT_LANGUAGE.search(text + " " + str(review.get("verdict", ""))):
        problems.append("verdict language contains probabilities or guarantees (§7.3.3)")
    if not 1 <= len(review.get("principal_reasons", [])) <= 5:
        problems.append("principal_reasons must have 1..5 items")
    for fb in review.get("feedback", []):
        if fb.get("evidence_available") not in ("none", None) and not isinstance(fb.get("evidence_available"), list):
            problems.append(f"{fb.get('feedback_id')}: evidence_available must be a list of Engine ids or 'none'")
    return problems


def next_step(review: dict, round_no: int) -> str:
    """Writer <-> Recruiter loop control (Master §3.10): stop after round 3 whatever the verdict."""
    if review["verdict"] == "Pasa a entrevista":
        return "deliver_to_user"
    if review.get("next_round_useful") is False:
        return "ask_user_for_evidence"  # rewording cannot fix missing Engine facts (no futile strict round)
    if round_no >= config()["limits"]["recruiter_rounds_max"]:
        return "deliver_with_reasons"   # UT-13: no indefinite loops
    return "revise"
