# Writer output contracts (condensed from knowledge/specs/writer.md §6.4-6.7)

## Draft Result (`outputs` of draft / revise)
```yaml
preparation_id: string
opportunity_ref: string
version: {version_id, number: 1|2|3|null, label: v1|v2|v3|uc_<n>, parent_version_id, published_at, folder}
documents_plan:
  basis: stated | default_not_stated
  documents: [{type: cv|cover_letter|selection_criteria|screening_responses|other, formats: [docx, pdf], limits, source: snapshot|default|user_approved}]
documents: [{type, files: [{format, path, hash, page_count}], limits_ok: bool}]
requirements_coverage: [{req_ref, kind, status: addressed|gap_no_evidence|not_applicable, addressed_in: [{document, location}], claim_ids, transfer_bridge}]
claim_evidence_map: [Claim Entry]
company_research_level: complete | limited | none_available
company_sources: [{source, url_or_id, accessed_at, used_for, type: fact|inference}]
missing_fact_requests: [{request_id, package_ref, req_ref, claim_needed (es), why_needed, document_section, current_handling: omitted|adjacent_evidence_used|placeholder_visible, deadline, resolution_path: add_to_jae}]
feedback_applied: [{feedback_id, status: applied|partially_applied|not_applied, reason}]
change_summary: string          # Spanish, <= 6 lines
validation:
  deterministic: {plan_match, claims_mapped, facts_match_jae, limits, au_spelling, banned_terms, unchanged_sections, injection_text_absent}   # pass|fail
  engine_pipeline: {all_passed, engine_unchanged}
  self_review: [{dimension, rating: meets|improvable|fails, blocking, note}]
voice: {skill_version: "1.0.0", decisions_version_read, mode: single_version|variants}
voice_review:                   # REQUIRED for draft and revise (voice-layers.md; task validate rejects it missing)
  order: [generate, soul_voice, humanizer, fact_verification]
  soul_voice: {loaded: [voice-profile.md, decisions.md, examples.md, voice.md], sector, changes: [text]}
  humanizer: {loaded: true, patterns_fixed: [n], overridden_by_soul_voice: [text], remaining_tells: text}
  naturalness_check: "pass | warnings: N"
send_status: blocked_until_user_sends
```

## Claim Entry
```yaml
claim_id: C-<version>-<n>
document: cv | cover_letter | selection_criteria | screening_responses | other
location: string            # section + short quote
text: string                # sentence as it appears
jae_ref: string             # REQUIRED: facts/evidence.yaml id, roles.yaml id or credentials.yaml id
recorded_fact: string       # the Engine wording it relies on
dimensions_checked: {role_verb, scope, metric, dates, seniority, authorship, certainty}   # pass | n/a
transformation: verbatim | rephrased | summarised
```
Non-factual sentences (motivation, interest, style) carry no claim_id.

## Status rules
- `success`: version published, all validations pass (may include gaps + Missing Fact Requests).
- `partial`: published with an unresolvable deterministic validation, declared in issues. Never for integrity.
- `blocked`: vigencia, snapshot, Engine, voice skill, unauthorised document, round limit, external action.
- `error`: unrecoverable render/file failure.
A version with any claim lacking a valid jae_ref is not published under any status.
