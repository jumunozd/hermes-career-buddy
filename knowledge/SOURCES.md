# Knowledge sources: authority, copies and hashes

Copied 2026-11-13 from the read-only source folders (archived in full in `private/sources/` since 2026-11-17). Controlled copies are write-protected
(`chmod a-w`). To update one: replace it from the source, record the new hash here, bump the
skill/instruction version and rerun `tests/`.

## Controlled copies (inside this project)

Re-pinned 2026-11-17 after P-5. The five role specs differ from the originals ONLY by the P-5 name
replacement (the user's first name -> "the user" / "el usuario", `juan-writing-voice` ->
`candidate-writing-voice`); verified by re-applying that transformation to the originals, which are
archived byte-identical in `private/sources/openai-skills-and-documents/`.

| File | Source | Version | SHA256 (first 16), current | Original (first 16) | Used by |
|---|---|---|---|---|---|
| `specs/Career_Development_OS_Master_Specification.md` | OPENAI folder | 1.0 (2026-11-07) | 1310b43074384eb3 | same | all roles (rules authority) |
| `specs/project-manager.md` | OPENAI folder `AGENTS/` | 1.2.1 (2026-11-13) | d6d0b9a53dbdf2c5 | 6fb05d94fd572aef | `hcb-project-manager` |
| `specs/job-hunter.md` | OPENAI folder `AGENTS/` | 1.2.1 | 4fa9678076fc3694 | 7fefc9152ad56b4e | `hcb-job-hunter` |
| `specs/research-agent.md` | OPENAI folder `AGENTS/` | 1.1.1 | 81202f88dd4bc01f | 218046e2795cd26b | `hcb-research-agent` |
| `specs/writer.md` | OPENAI folder `AGENTS/` | 1.0.1 | 7dd62af94d5fc996 | aadbd7a7c7df242f | `hcb-writer` |
| `specs/recruiter.md` | OPENAI folder `AGENTS/` | 1.0.1 | 611067d0b444e64e | 98791c0174f7cfa5 | `hcb-recruiter` |
| `private/knowledge/kb/job_hunter_intelligence_tasmania_2026-11-07.md` (private zone since P-5) | OPENAI folder | KB 1.0 | b33b0178a44b778b | same | Job Hunter, Research Agent |
| `../.hermes/skills/career-buddy/candidate-writing-voice/` | OPENAI folder `juan-writing-voice/` | 1.0.0 | SKILL b0711d626180d2c7 | SKILL a72c24c1ec669558 | Writer (voice layer); `decisions.md` is the live copy |

## Writer pack (distilled from the Engine, 2026-11-14)

| File | Built from | How it stays current |
|---|---|---|
| `hcb-writer/references/method.md` | Engine `rules/cv.md`, `rules/cover-letter.md`, `rules/template.md`, `voice/precedence.md`, `FEEDBACK_2026-10-21_taswater.md` | Hand-distilled; refresh when those Engine files change (`git -C <Engine> log rules/ voice/`) |
| `hcb-writer/references/voice.md` | Engine `voice/sector-*.md`, `voice/anti-slop.md`, `voice/approved-bullets.md`, `voice/samples.md` | Hand-distilled; same refresh rule |
| `hcb-writer/references/schemas.md` | `targets.yaml` / `content.json` that passed all Engine checks + `select_evidence.py --tags` | Refresh if the Engine generators change |
| `private/writer/facts-digest.md` | `private/facts/*.yaml` (referees excluded) | **Generated** by `bin/hcb writer-pack`, stamped with source hashes; `--check` and `bin/hcb doctor` flag staleness. Git-ignored (personal data) |

The Writer and Recruiter load these with `skill_view` instead of opening Engine files.

## Referenced in place (never copied: single source of truth)

| Authority | Path | Why not copied |
|---|---|---|
| Job Application Engine (facts, CV/letter/SC method, build + verification scripts) | `private/facts/` + `engine/` (copied from the Job Application Engine 2026-11-17, P-5; the Engine folder is no longer read) | Master §2.1: only authority for the user's facts; a copy would drift. Used read-only; integrity fingerprint checked around every pipeline run |
| A-H evaluator (prompt, schema, validator) | `private/ah-evaluator` (unchanged copy of the former `CareerDevelopmentOS/hermes2/job-evaluator`, 2026-11-17) | Master §6.3: must not be reimplemented. Imported read-only by `hcb/ah_adapter.py`; its pinned Engine hashes still match (checked by `bin/hcb doctor`) |
| Baserow token | `~/.hermes/career-buddy/secrets/baserow-token` | Secret; read only by `hcb/baserow.py` (owner/600/no-symlink checks), never by the model |

## Not used (and why)

| Item | Reason |
|---|---|
| Engine `archive/` | Engine rule: history, never a source |
| Engine `RUNBOOK_ANTIGRAVITY.md`, `AUDIT_2026-08-10.md`, old CHANGELOG | Superseded build history of the Engine refactor |
| Engine `voice/*.md` | Engine's own wording rules stay in force through its scripts; the approved voice layer is `candidate-writing-voice` (writer.md §3.6) |
| `candidate-writing-voice-v1.0.0.zip` | Identical to the unpacked folder (same 9 files) |
| KB v2.0 (`claude/job_hunter_intelligence_master_2026-11-12_v2.md`) | Cited by the specs but not present in either source folder: see RECONCILIATION in docs/ARCHITECTURE.md |
