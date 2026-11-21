# Recruiter Review Result (condensed from knowledge/specs/recruiter.md §6.4-6.6)

`bin/hcb review <file> --round N` reads these exact keys.

```yaml
review_id: string
opportunity_ref: string
preparation_id: string
round: 1 | 2 | 3
mode: strict | strategic                 # strategic only in round 3
documents_version_ref: string            # version folder
eligibility_flag: 8579-OK | 8579-Check | 8579-Fail
verdict: Pasa a entrevista | No pasa a entrevista   # must equal computed verdict
verdict_basis: strict | strategic
principal_reasons: [{reason (es), refs: [requirement_id | claim_id]}]    # 1..5
gates: {G1_integrity, G2_documents, G3_legal, G4_essential, G5_blocking_quality}   # pass|fail
requirements_assessment:
  - {requirement_id, text_quote, category: legal_gate|pre_employment_check|essential|desirable|ambiguous|document_requirement,
     evidence_status: met|transferable|in_jae_not_in_document|partial|absent|undeterminable,
     document_quote, jae_ref, transfer_bridge, potential_acceptance: null | justification}
document_compliance:
  - {document_type, present: bool, format_ok: bool, limits: {declared, measured, ok}, criteria_addressed: [{criterion_id, addressed}], unrequested_document: bool}
claims: [{claim_id, document, location, text_quote, claim_status, jae_ref, discrepancy}]   # only non-supported / non-factual-excluded
claims_summary: {supported_ids: [claim_id], non_factual_ids: [claim_id]}
next_round_useful: true | false        # false when only Engine-missing evidence fails
integrity_defects: [claim_id]
quality_assessment: [{dimension, rating: meets|improvable|fails, blocking: bool, evidence}]
feedback:
  - {feedback_id: FB-<round>-<n>, priority: blocking|important|optional, category, requirement_id, claim_id,
     document, location, problem (es), evidence_available: [jae_ref] | "none", instruction, do_not, expected_result}
evidence_gap_requests: [{request_id, requirement_id, question (es), resolution_path: add_to_jae}]
strengths: [text]
perception_risks: [text]
send_readiness: ready_for_human_review | not_fit_to_send
disclaimer: "Simulación de revisión documental basada en el anuncio y en evidencia verificada. No predice la decisión real del empleador."
```

Gate rules (deterministic, recruiter.md §7.3.1):
- G1: zero claims overstated / unsupported / contradicted.
- G2: required documents present, right format, within limits, all criteria answered, no unrequested document.
- G3: every legal_gate `met`; eligibility_flag != 8579-Fail.
- G4: strict rounds: every essential `met` or `transferable`. Round 3: up to 1 essential `partial`/`absent`
  accepted by potential with justification (never legal gates, documents or integrity).
- G5: no blocking rubric dimension rated `fails`.
Desirable never blocks; ambiguous/undeterminable never decides alone; pre-employment checks don't count.
