# Status register (updated 2026-11-17)

Legend: **Specified** = designed and documented · **Implemented** = files/config/integration exist ·
**Validated** = passed a test with the real runtime or real artefacts (evidence in `private/test-evidence/` since P-5).
Nothing is "operational" unless it is Validated.

## Capabilities

| Capability | Specified | Implemented | Validated | Evidence / note |
|---|---|---|---|---|
| Hermes discovers project, loads `AGENTS.md` | ✔ | ✔ | ✔ | RT-01 |
| 6 project skills indexed + `skill_view` load | ✔ | ✔ | ✔ | RT-01 (writer skill fixed after skills-guard finding) |
| PM orchestration via `delegate_task` (Writer → Recruiter) | ✔ | ✔ | ✔ rounds 1-3 | RT-02, RT-02b, RT-02c |
| Task Envelope / idempotency / contract validation | ✔ | ✔ | ✔ unit + runtime rounds 1-3 | tests, RT-02b, RT-02c |
| Command vocabulary + report-number resolution | ✔ | ✔ | ✔ unit/CLI | tests, RT-04 |
| Approval records; approval not extended by similarity | ✔ | ✔ | ✔ unit | tests |
| Fit > 50 % threshold, C1-C11, Top 5 not padded, 3 exploratory | ✔ | ✔ | ✔ unit + report | tests, RT-04 |
| A-H evaluator reuse (original validator) | ✔ | ✔ | ✔ on real Glenorchy result (59/100) | contract test |
| A-H isolated inference for a new ad | ✔ | ✔ | ✔ PRELIMINARY run (scores withheld as designed; injected credentials rejected) | RT-05 |
| Engine pipeline (CV/letter render, verify, ATS, keywords) from project folder | ✔ | ✔ | ✔ replay; Engine unchanged | engine replay |
| Tailored CV + cover letter for a new ad (Writer) | ✔ | ✔ | ✔ runtime | RT-02 |
| The user Writing Voice applied by Writer | ✔ | ✔ | ✔ loaded and applied (voice fidelity needs the user's judgement) | RT-02 |
| Recruiter review, deterministic gates G1-G5, ≤ 3 rounds | ✔ | ✔ | ✔ unit · ✔ runtime runtime | tests, RT-02 |
| Untrusted ad instructions ignored | ✔ | ✔ | ✔ runtime | planted line in test ad, RT-02 |
| Versioned, immutable packages + manifest hashes | ✔ | ✔ | ✔ runtime | RT-02 |
| Baserow read (live), schema drift check | ✔ | ✔ | ✔ live | RT-03, contract test |
| Baserow dedup + mapped create/update | ✔ | ✔ | ✔ dry-run only | RT-03 |
| Baserow live write + read-back | ✔ | ✔ schema v2, `register` + `backfill` | ✔ live 2026-11-19: 5 rows written and verified (26-30) | P-6 |
| Telegram commands/delivery | ✔ | ✔ bot on profile `career-buddy`; digest sent by code (`bin/hcb daily-send` -> `hermes send`) | ✔ live 2026-11-17: test digest delivered (message 53+), recorded once, idempotent | — |
| Weekly report (≤ 3 pages, number map) | ✔ | ✔ | ✔ synthetic snapshot (1 page) | RT-04 |
| Gmail delivery of the report | ✔ | ✘ | ✘ | TV-07/TV-10 pending |
| Follow-up at 10 days (recommend only) | ✔ | ✔ | ✔ unit + report | tests, RT-04 |
| Daily new-offer digest + call suggestion (D-USR-01) | ✔ | ✔ `hcb/daily.py`, `bin/hcb daily`, `bin/hcb contacts` | ✔ unit + CLI (synthetic); delivery needs Telegram | tests/test_daily_alert.py |
| Weekday discovery (Job Hunter `search`) | ✔ | ✔ skill + deterministic sweep (`bin/hcb sweep`); group A page_read sources enabled (Hydro withdrawn) | ✔ live, manual runs RT-13/14/14b/15 (RT-15: 10.8 min); not scheduled yet | P-3 for SEEK/LinkedIn alerts |
| Friday market review (Research) | ✔ | ✔ skill | ✘ | needs web tools + approval |
| Interview preparation (2 documents) | ✔ | ✔ skills | ✘ | next validation step |
| Scheduled cron jobs | ✔ | ✔ all three installed (profile `career-buddy`, failures to Telegram): weekday aa639c87a2bb, Friday 8f98c9127775, Saturday ea20eb1adf2a | ◐ weekday: 3/5 runs ok 18-19 Nov (2 failed on a provider outage, 1 delayed 45 min: Mac on battery asleep); Friday/Saturday first runs 20-21 Nov | TV-09 |
| Secrets outside repo; injection-pattern scan | ✔ | ✔ | ✔ tests | security tests |

## Technical verification register (Master §11.4)

| ID | Item | State | Evidence / decision |
|---|---|---|---|
| TV-01 | Hermes version | **Verified** | v0.22.5 (2026.9.24), git install, commit bf0203a794a0, Python 3.14.9. Latest upstream per spec: v0.23.0. No update performed |
| TV-02 | Agent architecture | **Verified (RT-02)** | Default `delegate_task` + project skills; no extra profiles |
| TV-03 | advanced-delegation plugin | Not needed v1 | Not installed |
| TV-04 | Job Application Engine | **Replaced by P-5** (facts in `private/facts/`, method in `engine/`) | Read-only; selftest 4/4; pipeline replay passes from project folder; fingerprint guard |
| TV-05 | A-H evaluator | **Verified** | `private/ah-evaluator` (copied unchanged 2026-11-17); original validator reused; pins match Engine |
| TV-06 | Baserow | **Verified (read)** | localhost:8080 table 839, 11 fields; Status options lack the 3 confirmed semantics → Notes tags + MIG-01 |
| TV-07 | Gmail | Pending | Sender account and mechanism not chosen |
| TV-08 | Telegram | **Connected** | Bot on dedicated Hermes profile `career-buddy` (own .env, `terminal.cwd` = project); default profile has no Telegram |
| TV-09 | Schedule hours | **Decided** | Search + contacts + digest Mon-Fri 07:30/12:30/16:30; Friday review + maintenance 18:00; Saturday report 08:00 (Australia/Hobart, the user 2026-11-15). Not installed yet |
| TV-10 | Report format in Gmail | Pending | HTML + PDF produced locally |
| TV-11 | Models / Codex | Observed | Default profile already uses provider `openai-codex`; no provider change made |
| TV-12 | Mac vs VPS | Out of scope | No VPS work (per mission) |
| TV-13 | Deep Research source approval | Pending | KB v2.0 missing; all sources disabled |
| TV-14 | Costs / limits | Pending | Test runs used the existing Codex subscription |

## Changes made outside this folder (all approved)
- `~/.hermes/config.yaml`: `skills.trusted_project_dirs: ["<project folder>"]`
  via `hermes skills trust` (undo: `hermes skills untrust <path>`). Backup of the previous config in the
  session scratchpad.
- Hermes session/state files created by the test sessions (normal Hermes behaviour).
- 2026-11-17 (The user approved): new Hermes profile `career-buddy` (cloned from default; `terminal.cwd` = this
  folder); the Telegram token, allowlist and `platforms.telegram` moved there from the default profile; gateway
  restarted. Default profile memory cleared (career notes); profile `career-sandbox-pilot` deleted.
- 2026-11-17 (The user approved): old hermes2 pilot removed: `~/CareerDevelopmentOS/hermes2`, `~/CareerDevelopmentOS/jobsync`,
  Docker volume `career-os-hermes2-state`. The A-H evaluator was first copied unchanged to
  `~/.hermes/career-buddy/ah-evaluator` and the Baserow token moved to `~/.hermes/career-buddy/secrets/`.
  Backups (tgz, profile export, old memory, old config/.env): `~/.hermes/career-buddy/backups/`.
  Kept: `~/CareerDevelopmentOS/{AGENTS.md,baserow-integration,outputs,test-files}`, the Baserow container and data.
- No changes to the Job Application Engine, Baserow data, Hermes code, plugins or cron.

## Remaining dependencies (in order, updated 2026-11-17)

Done: initial commit (`d86aa5d`); Telegram bot on Hermes profile `career-buddy`, project context verified from a
fresh Telegram session; source list approved and group A enabled (JH-TV-02, `web_discovery: true`).

| # | Step | Who | Unblocks |
|---|---|---|---|
| 1 | Turn on `features.telegram_delivery` and run one real digest to Telegram (send + `bin/hcb daily-delivered`) | You approve, Claude Code tests | Digest delivery (TV-08) |
| 2 | Install the three jobs from `config/schedules.yaml` with `--workdir` = this folder, profile `career-buddy` | You approve, Claude Code installs | Mon-Fri / Friday / Saturday cycle |
| 3 | Baserow live writes: add Create + Update (never Delete) on table 839 to the dedicated token, set `features.baserow_live_writes: true`, then approve one marked test record + read-back | You | Real registration, Cerrada, references (TV-06) |
| 4 | Decide MIG-01 (new Status options Exploratoria / Pendiente de revisión / Cerrada + Fit, Ranking Category, Opportunity Ref, Latest Version fields) after a Baserow backup | You | Native Baserow views instead of Notes tags |
| 5 | Failure-injection tests of Master §13.5 (Baserow down, Telegram failure mid-delivery, restart during a cron run) once 2, 3 and 6 exist | Claude Code | Acceptance §14 |
| 6 | Gmail for the Saturday report (TV-07, TV-10; note: sending needs its own decision, P-3 is read-only): pick sender + mechanism (Hermes email gateway or the `himalaya` skill), test a marked email to yourself | You | Saturday delivery |
| 7 | Validate interview preparation end to end (`Entrevista [ID] [fecha]` on the synthetic package) and Research `market_review` with web tools | Claude Code | Interview flow, Friday review |
| 8 | Voice fidelity: run `candidate-writing-voice/references/cases.json` and record your choices in `decisions.md` | You + Writer | Voice validation |
| 9 | **P-3 email alerts (PENDING: the user's manual setup)**: account decided (D-P3-1 = A, dedicated alerts Gmail, 2026-11-16): create that account, create the Gmail label + filter `Career Buddy/Alertas`, create the alerts on the 13 portals listed in docs/proposals/P-3.md, create the Google Cloud OAuth client (gmail.readonly only), approve P-3. Then Claude Code builds `hcb/mail.py` + parsers from the first real emails and runs RT-16 | You, then Claude Code | SEEK, LinkedIn, Hydro, TasNetworks, TasWater, TasPorts, Bell Bay, Marinus coverage |
| 10 | Publish on GitHub (create the repository, add a LICENSE); later the Hostinger move (docs/DEPLOYMENT.md) | You | Portfolio, server |
| 11 | Off-disk copy of the daily backup (iCloud Drive recommended, `backup.extra_destinations`): the user decided 2026-11-19 to do it once the system is finished | You decide, Claude Code configures | Protection against losing the Mac |

## Change log after the initial build
- 2026-11-13 · D-USR-01 daily new-opportunity digest with call suggestion (`hcb/daily.py`).
- 2026-11-14 · **Engine write, user-authorised (AP-5e8010ad24223242164ac8de):** one entry
  `ecyt_excel_business_report` added to `facts/evidence.yaml` with the exact wording the user approved
  (answers MFR-TEST-001). Only Engine change ever made by Hermes Career Buddy.
- 2026-11-14 · **A-H manifest repin, user-authorised (AP-58f12c43e543f77ba6e6b28e):** project-local copy
  `config/ah-manifest.repinned.json` (new evidence.yaml hash + the new id in the evidence projection).
  The original evaluator in CareerDevelopmentOS is unchanged. `hcb/ah_adapter.py` uses the copy only
  while that approval record exists. Any future Engine fact change blocks A-H again until a new repin.
- 2026-11-14 · **Writer pack** (`hcb-writer/references/method.md`, `voice.md`, `schemas.md`, generated
  `facts-digest.md`; `bin/hcb writer-pack [--check]`). Writer/Recruiter skills v1.1.0 load the pack instead of
  Engine files. Token saving measured in RT-06.
- 2026-11-14 · RT-02d: after the new evidence, v4 passed the **strict** review (R-08 met, 0 integrity defects).
- 2026-11-14 · **Job Hunter target catalogue** (`config/job-targets.yaml` from the user's "Cargos objetivos" file,
  controlled copy in `knowledge/kb/`); deterministic matcher `bin/hcb targets match|queries`; Job Hunter skill v1.1.0.
  Search frequency confirmed by the user 2026-11-14: DAILY, weekends included (overrides catalogue §8.1).
- 2026-11-14 · RT-06 pack measurement (Writer -41% input, -56% output, -60% cache) and RT-08 first real ad (Shaw).
- 2026-11-14 · Daily Job Hunter search + digest at **05:00 and 21:00** Australia/Hobart, every day (The user).
- 2026-11-14 · **Recruiter review brief** (`bin/hcb review-brief`), Recruiter skill 1.2.0 (brief-only reads, rubric
  inline, compact output, futile-round signal), PM 1.1.0 (no futile strict rounds), Writer 1.2.0 (cite every merged
  fact). RT-09: Recruiter input -59%, cache -77%, same verdict.
- 2026-11-15 · Engine entry `hermes_career_buddy_multiagent` (AP-0a5fd9054233ec05171cdc96) + A-H manifest repin (both new ids in projection).
- 2026-11-15 · **P-1 applied** (AP-9a87dab3396a1e3e2e676882): Entry Signal v1.0 (7 indicators, critical 1/5/6) in `config/job-targets.yaml`, `bin/hcb targets entry-signal`, Job Hunter 1.2.0, daily digest 'Te acerca a'. Shaw -> Neutral. See docs/proposals/P-1.md.
- 2026-11-15 · Engine fact `identity.msic` (AP-c3a9f9319f12b0b5e18e28f5; identity.yaml is outside the A-H manifest, no repin). Fix: `review_brief._refs()` dropped a bare `identity` ref (false G1 fail in RT-11); regression asserts added. TasPorts v2 re-review (AP-6e5fe2228e3a9dab90f29ca7): Pasa a entrevista, ready_for_human_review. See tests/results/RT-11_tasports_v2.md.
- 2026-11-15 · **P-2 applied** (AP-ea17780d4846d8c90c64ab11): `config/contact-policy.yaml`, `hcb/contacts.py`, `bin/hcb contact policy|trigger|validate|lint`, digest 👤/⛔ lines, `Prepara contacto [ID]`, new actions contact_research / outreach_draft / outreach_check, skills JH 1.3.0, RA 1.1.1, Writer 1.3.0, Recruiter 1.3.0, PM 1.2.0, amendments in docs/SPEC_AMENDMENTS.md. Implemented; deterministic layer validated; live research validated in RT-12c after the user-approved Hermes web backend change (Exa free for search + extract). `features.contact_research: true`.
- 2026-11-15 · **Duplicates:** Seen-Postings Log in code (`hcb/seen.py`, `bin/hcb seen check|add`, state/seen.jsonl; SEEK job id on any URL incl. au.seek.com), digest announces each offer once (state/notified.jsonl), contact research never twice per offer. JH skill 1.4.0.
- 2026-11-15 · **D-USR-02 schedule** (AP-19d0bccce02dfb3ac2b94a8c): Job Hunter + contacts + digest Monday-Friday at 07:30, 12:30, 16:30 Hobart (`30 7,12,16 * * 1-5`); silent empty runs. Not installed (cron pending TV-08 / sources). PM skill 1.3.0.
- 2026-11-15 · Friday market review + maintenance at 18:00, Saturday report at 08:00 (both confirmed; TV-09 resolved for every job).
- 2026-11-16 · **JH-TV-02 source verification** (docs/SOURCE_VERIFICATION.md): 30 portals checked (robots, real read, terms). **Group A enabled** (AP-338e1986beb43f61360209de): TSS, Glenorchy, Devonport, Hydro/Entura, Bell Bay, Nyrstar, Huon, TasRail, SAGE, Hazell Bros, page_read only, paced; `bin/hcb sources due` applies cadence per run; `features.web_discovery: true` for these only. SEEK/LinkedIn/Indeed/UTAS/Incat stay off for direct reading. Live Job Hunter search with these sources not yet run (RT-13 pending). JH skill 1.5.0.
- 2026-11-16 · **RT-13** live search (PARTIAL): 42 ads from 7 sources, 6 candidates, A-H PRELIMINARY only. 6 defects fixed (TSS URL, Seen keys, enforced pacing `bin/hcb sources read`, digest refs `o-xxxxxx`, generic title match, zone before A-H). JH skill 1.6.0, PM skill note. See tests/results/RT-13_search.md.
- 2026-11-16 · **P-4 option B applied** (AP-8b0ed42a08712e3b6d21afc1): digest + Top 5 ranked by alignment with target roles (`ranking.basis: alignment`, rules A0-A4, `alignment_key`), no A-H during search, out-of-catalogue hidden, A-H VERIFIED only at `Prepara` via `bin/hcb ah vacancy-open` (accepted by the original evaluator). JH 1.7.0, PM 1.4.0, amendment A-02. Not yet re-run live (RT-14).
- 2026-11-16 · **RT-14 run** (live, second Monday 07:30 run): PARTIAL. P-4 B and the RT-13 fixes confirmed live; tokens -39 % vs RT-13, but 32 min, 0 Seen skips. Four defects fixed the same day: Seen status from the card identity (company+title+location+closing) instead of the passed text; listing-card triage `bin/hcb triage` (zone + title) before any detail read, with `out_of_field_titles`; region-only locations (`South`, `North West`) -> `pendiente_revision` "confirmar localidad" (rule A2-LOC) instead of dropped; catalogue title with clinical/lab/classroom duties -> `needs_review` "revisar funciones" (`field_mismatch_signals`). JH 1.8.0. 111 tests OK. Offline replay of RT-14: 35 known_unchanged (was 0), 10 detail reads (was 35). RT-14b (live re-run) in progress. Evidence of the first run: state/RT-14-run1/.
- 2026-11-16 · **RT-14b** (live re-run with the 4 fixes): fixes confirmed (Senior Policy and Project Officer now first in the digest; Technical Officer "revisar funciones"), but 66 min / 116 reads. **Deterministic sweep** added (A-03): `bin/hcb sweep`, `hcb/sweep.py`, sources.yaml 1.2.0 (job_link, pages, title_filter, employer, default_location), strict title filter for TSS and councils, Saturday count of title-only discards, Seen job-unique key. JH 1.9.0. Live sweep: 164 s, 0 tokens, short list 1. 117 tests OK. Hermes run with the sweep (RT-15) not yet done.
- 2026-11-16 · **RT-15** (Hermes + sweep, simulated Tue 07:30): 10.8 min, 8 reads, 138K input (RT-14b: 66 min, 116 reads, 253K). Found that Hydro's listing is served from a PageUp host with robots `Disallow: /`: **EMP-HYDRO disabled**. Unread jobs no longer go to the Seen log (7 Hydro rows removed). Hazell detail host allowed (robots checked). Bell Bay unreadable (Workday). 117 tests OK.
- 2026-11-16 · **P-3 proposed** (docs/proposals/P-3.md): email job alerts into a Gmail label, read with a `gmail.readonly`-only token (not the stock google-workspace skill, which asks for send/modify/Drive), parsed deterministically into the sweep pipeline. Waits for the user's alert setup (dependency 11).
- 2026-11-17 · **Telegram connected + hermes2 cleanup** (The user approved): bot on Hermes profile `career-buddy`, A-H evaluator and Baserow token relocated under `~/.hermes/career-buddy/`, old hermes2/jobsync/sandbox removed after backup. 117 tests OK, doctor OK, Baserow live read OK.
- 2026-11-17 · **P-5 implemented** (user approved): self-contained project with a public / private split. Personal data in `private/` (gitignored), CV method + scripts in `engine/`, synthetic persona in `examples/candidate/`, `bin/hcb privacy-scan` + pre-commit hook. 122 tests OK on both personas; Nyrstar CV re-rendered identical; Engine folder no longer read (sandbox check). Details: docs/proposals/P-5.md.
- 2026-11-17 · **Three fixes from Hermes's own review:** (1) a saved digest is `pending`; offers become notified only via `bin/hcb daily-delivered` after a confirmed send, a failed send brings them back next run; (2) the digest orders by category then `rules.alignment_key`, the same key as the Top 5; (3) `config/schedules.yaml` called a non-existent `bin/hcb report build`: fixed, and `tests/test_instructions.py` now checks every `bin/hcb` command named in schedules, AGENTS.md and skills. Weekday job `deliver: local` (the PM sends and records). 127 tests OK.
- 2026-11-17 · **Second Hermes review (Telegram), 6 points:** (1) `web_discovery` now blocks every source read in code (`hcb/sources.py`); (2) an ad with a no-approach clause gets no call hint and no researched contacts in the digest; (3) digest retries never overwrite a saved file; (4) `knowledge/SOURCES.md` re-pinned: the role specs differ from the originals only by the P-5 name replacement (verified); (5) README switches, this register's dependencies and the PM delivery condition (`telegram_delivery`) reconciled; (6) Telegram sessions opened before P-5 carry stale context: start a new one with `/new`. 129 tests OK.
- 2026-11-17 · **Launch (user approved):** `telegram_delivery` ON with deterministic `bin/hcb daily-send` (hermes send, no LLM; `hermes send` exits 0 on failure, so only a `message_id` counts as delivered); live test digest delivered and recorded once. Gateway installed as launchd service (`~/Library/LaunchAgents/ai.hermes.gateway.plist`, wraps the gateway in `/usr/bin/osascript` for macOS Local Network permission), Telegram reconnected. Weekday search cron installed (job aa639c87a2bb, 07:30/12:30/16:30 Mon-Fri, deliver local, failures to Telegram). Mac: AC sleep disabled by the user (`pmset -c sleep 0`). Undo: `hermes -p career-buddy cron remove aa639c87a2bb`, `hermes gateway uninstall`, `sudo pmset -c sleep 1`.
- 2026-11-17 · **One-time fallback for the first unattended day (the user):** `daily_alert.fallback_once` (2026-11-18 only): an empty run with nothing delivered earlier that day sends the best 3 offers already found (alignment_key; closed, ungrouped and the false match 'Senior Electrical Design Engineer' excluded). `notified_ids()` now counts only confirmed deliveries: 14 legacy rows from the pre-fix save() (never sent) no longer hide offers. Tests no longer write into `private/reports/` (23 test-made digests moved to `private/test-evidence/test-run-digests/`). The PM always runs `daily` + `daily-send`, also on empty runs; installed job prompt updated. 136 tests OK.
- 2026-11-17 · **Rule change (the user): Senior roles excluded.** `job-targets.yaml excluded_title_words: [senior]`: triage logs them from the card (`seen_log:seniority_excluded`), the digest and the one-time fallback never show them. The fallback also skips 'revisar funciones' offers, so on 2026-11-18 it would send 1 offer (Library Operations Coordinator). 138 tests OK.
- 2026-11-17 · **Rule change (the user): Lead, Principal and Manager excluded too** (`excluded_title_words: [senior, lead, principal, manager]`, whole words: 'Leading Hand' and 'Management Accountant' still pass). Tomorrow's fallback unchanged (1 offer). 139 tests OK.
- 2026-11-17 · **Rule change (the user): library roles are another profession** (`out_of_field_titles` + library, librarian). Tomorrow's fallback now has no good candidate, so on 2026-11-18 an empty run sends ONE status line ('primera corrida automática OK…') instead of offers, once that day. 140 tests OK.
- 2026-11-17 · **Catalogue changes (the user):** Remote Feed Operator / Feed Operator added to group E (exploratory entry); Trades Assistant and Construction Materials Tester added to `out_of_field_titles`; Project Officer stays (group C). The one-time fallback re-matches stored records against today's catalogue: on 2026-11-18 an empty run would send Remote Feed Operator (Huon, closes 27/11). 141 tests OK.
- 2026-11-17 · **More title choices (the user):** maintainer, dispatcher, customer service added to `out_of_field_titles`. Technical Officer stays a catalogue title (group D); the clinical-lab one (526015) is already 'revisar funciones', never in the fallback, and as a seen job it is not announced again. 142 tests OK.
- 2026-11-17 · **Prepare from a saved ad:** `Prepara la oferta … private/state/ads/<file>.txt` parses as `prepare by ad_file` (was 'sin números u IDs'); PM skill step added. Stornoway ad (SEEK, pasted by the user) saved. One-time Telegram reminder for 2026-11-18 08:00 (job 4ea53e6709b0, no LLM, script in the career-buddy profile). 143 tests OK.
- 2026-11-19 · **First unattended runs reviewed:** 18/11 07:30 ok (1 offer delivered, msg 56), 08:00 reminder delivered, 12:30 and 16:30 failed (OpenAI provider outage, ~47 min wait each, recovered), 19/11 07:30 ran 08:15 (Mac on battery slept; `pmset -c sleep 0` covers AC only) and stayed silent (nothing new). Stornoway prepared from Telegram (v1-v3). **Friday + Saturday jobs installed** (user approved). New `bin/hcb report-send`: weekly PDF to Telegram via `hermes send` (copied to a space-free temp path; no `[...]` in the caption, which made hermes drop the attachment); live test delivered (msg 77). 144 tests OK.
- 2026-11-19 · **P-6 approved (Baserow schema v2):** Baserow is Hermes's own database and holds only non-discarded offers. Backup taken (fields, rows, full DB dump). `bin/hcb baserow migrate-schema` ready (preview: 12 fields + Status 'Closed'); `--apply` waits for the user to run it in a terminal. 147 tests OK.
- 2026-11-19 · **Baserow schema v2 live (P-6 steps 1-2, 4):** 12 fields + Status `Closed` created by the user; Status is single_select; schema-check clean; adapter writes the new fields. Pending: token Create + Update permission (user), backfill preview of the kept offers, then `baserow_live_writes`. 147 tests OK.
- 2026-11-19 · **Baserow live (P-6):** writes ON, 5 offers backfilled and verified, weekday runs register non-discarded offers via `bin/hcb baserow register`. Tests can no longer write to the real Baserow (a test created row 31 'TEST' before the guard; the user deletes it). 151 tests OK.
- 2026-11-19 · **P-7 live:** Documents (6 PDFs) and Contacts (7 rows, one duplicate to delete) written and verified; one contact per person from now on. 155 tests OK.
- 2026-11-19 · **Daily encrypted backup** (user request): `bin/hcb backup` + Hermes cron `daily-backup` 03:00 (job 3e3e37b0ac1e, no LLM, failures to Telegram). First run 10 s, 176 MB, verified; full restore test passed. Off-disk copy pending the user's choice of destination. Contacts: one networking contact added (follow-up 23/11).
- 2026-11-20 · **Facts changed by the user (2026-11-19)** and **A-H manifest re-pinned** (AP-984ea633af81459c3c707581): AI Fluency course added to credentials (A-H sees it); Panorama and Utility Worker end dates (2026). **P-9 proposed** (CV engine v2). 158 tests OK.
- 2026-11-20 · **P-9 CV engine v2 implemented** (all decisions approved): summary as the hook with proven claims, projects section, thematic headings, derived percentages, wider skills, page footer, heavy-industry register and the four guards. 164 tests OK.
- 2026-11-20 · **Compact CV layout** (user): `layout: compact` (smaller type, tighter spacing, left-aligned, low header, slim page footer) and optional bullet headlines; dates follow the employer (PDFKit split far-right or bold dates). Networking CV v13: 2 pages with room, all checks OK. 164 tests OK.
- 2026-11-20 · **P-10 part 1 (Telegram Top 3 + Prepare Docs button)** implemented: daily message by code, inline buttons, idempotent prepare-request, plugin `career-buddy-buttons` enabled in the profile. Live tap test pending. E-mail delivery blocked (iCloud storage full). 166 tests OK.
- 2026-11-20 · **P-10 part 1 validated live**: Prepare Docs button and text confirmation in the chat both work (tests 1 and 2); unknown offers refused. Part 2 (e-mail delivery) still blocked on the mailbox (iCloud full). 167 tests OK.
- 2026-11-21 · **P-12 proposed** (employer catalogue and alert coverage): first-pass check of 54 Tasmanian engineering employers; 14 readable (group P), 25 on job platforms best covered by e-mail alerts (group W), the rest blocked, URL to find or out of zone. SEEK, LinkedIn, TasNetworks by e-mail alerts (P-3). Waiting for the user's decisions.
- 2026-11-21 · **D-P12-1 decided (the user): alerts mailbox = the dedicated iCloud mailbox** (IMAP, read-only enforced in code), same mailbox as the package delivery; supersedes the Gmail choice of P-3.
- 2026-11-21 · **P-12 approved** by the user (all decisions, AP-634145ead1b69bc58ae5ba17). Next: employers.yaml, confirmation reads of group P, search_discovery for groups W/X; e-mail reader after the user's alerts and iCloud app password.
- 2026-11-21 · **P-12 implemented (part 1)**: Employer Registry (66), 9 new page_read sources (18 read in all), search safety net for 24 sources (bin/hcb discover inside the sweep, 12:30/16:30), cadences spread for the 180 s terminal limit. E-mail reader waits for the user's alerts and app password. 174 tests OK.
- 2026-11-21 · **P-13 proposed** (status page + read-only pipeline board, bin/hcb dashboard; Baserow Kanban/Calendar are Premium). docs/BASEROW_VIEWS.md: five free views for tracking.
- 2026-11-21 · **P-13 status page built** (AP-689edb7643cf91b9f7f12c2b): bin/hcb dashboard, read-only board from Baserow + system health + coverage + funnel, refreshed after each run. «Estado» on Telegram and VPS access still to decide. 179 tests OK.
