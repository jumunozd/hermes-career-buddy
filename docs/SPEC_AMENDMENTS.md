# Approved amendments to the controlled spec copies (knowledge/specs/, read-only)

The spec copies are not edited. Approved changes are recorded here; skills and code implement the
amended rule. The PM skill's "Full rules" pointer covers this file too.

## A-01 (P-2, AP-ea17780d4846d8c90c64ab11, 2026-11-15) Early hiring contacts
- research-agent.md §0 rule 9: exception for `contact_research`. The public professional role of at
  most 2 people tied to one specific vacancy, limited to the fields in config/contact-policy.yaml
  `contact_fields`. Panel members stay excluded.
- research-agent.md pitfall "deep research on every opportunity": contacts only for offers selected
  by `bin/hcb contact trigger` (fresh <= 24 h, principal or Strategic Entry, no no-approach clause,
  private employer, max 3 per run). Agency and government offers use only the ad's contacts.
- New actions: research_agent `contact_research`, writer `outreach_draft`, recruiter `outreach_check`.
  New command `Prepara contacto [ID]` (draft only).
- The draft skill's "Recruiter composes the message" is replaced by: Writer composes, Recruiter checks (G1).
- Unchanged: D-PM-03 (the system never sends or contacts), job-hunter.md §2.4 (the Job Hunter
  contacts no one and researches no people), the 10-day follow-up, and Master §9.1 (LinkedIn or other
  contact needs specific human approval: The user sends every message himself).

## A-02 (P-4 option B, AP-8b0ed42a08712e3b6d21afc1, 2026-11-16) Ranking by alignment
- Master §3.3 / job-hunter.md §6.7 (fit > 50 % gates the main ranking): replaced by the deterministic
  alignment with the target roles (config `ranking.basis: alignment`, `hcb/rules.py alignment_key`, rules A0-A4).
- job-hunter.md (A-H on every candidate during search): A-H runs only at preparation, VERIFIED, with
  the user's `Prepara` recorded as his vacancy-open confirmation (`bin/hcb ah vacancy-open`).
- Unchanged: the A-H evaluator itself, its rule that only the user can confirm a vacancy, gates C1-C6,
  Top 5 never padded, exploratory separate with a one-line justification.

## A-03 Deterministic sweep and strict title filter (RT-14 / RT-14b, el usuario 2026-11-16: "Déjala terminar y luego implementa el barrido")
- job-hunter.md search procedure: listing reading, card parsing, Seen check and card triage move from the Job
  Hunter (LLM) to `bin/hcb sweep` (hcb/sweep.py). The Job Hunter works only on the short list and on sources
  the sweep cannot parse (`needs_agent`). Coverage rules, pacing, identity and source permissions unchanged.
- "Never reject by title alone" gets two exceptions: (a) titles of another regulated profession
  (`out_of_field_titles`), on every source; (b) on big mixed boards (`title_filter: strict`: TSS, councils)
  a title with no catalogue match and no distinctive catalogue word. Both are logged in the Seen log
  (rule T0) and counted in the Saturday report under "Decisiones requeridas".
- Seen identity: a job-unique key (portal id, job number or #fragment) is the same job whatever company text.
- Rollback: JH skill 1.8.0 (agent reads listings) and remove `title_filter` from config/sources.yaml.
