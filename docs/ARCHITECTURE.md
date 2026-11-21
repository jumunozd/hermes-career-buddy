# Architecture and design decisions

## 1. How the specification maps onto Hermes v0.22.5 (installed, verified)

| Spec concept | Hermes-native implementation | Evidence it is real Hermes behaviour |
|---|---|---|
| One project context, no duplicates (Master §11.2.5) | `AGENTS.md` at the git root; `CLAUDE.md` only points to it | Hermes loads ONE context file, first match `.hermes.md` → `AGENTS.md` → `CLAUDE.md` (docs `context-files.md`); confirmed in RT-01 |
| Five logical roles (§3.1) | Project skills in `.hermes/skills/career-buddy/`: `hcb-project-manager`, `hcb-job-hunter`, `hcb-research-agent`, `hcb-writer`, `hcb-recruiter` | Project-local skills load after `hermes skills trust`; tagged `[project]`; confirmed in RT-01 |
| PM as user-facing coordinator | The main Hermes session (CLI / Telegram / cron) acts as PM per `AGENTS.md` | RT-01, RT-02 |
| Specialists (§12.4: "role contracts injected in each delegation") | `delegate_task` subagents. `bin/hcb task make` produces the Task Envelope + context telling the child which skill to load. Subagents automatically get `AGENTS.md` (docs `delegation.md`) | RT-02 |
| Independent Recruiter judgement | Recruiter always runs in a fresh subagent context, separate from the Writer | Hermes subagents start with a fresh conversation |
| Durable weekly cycle (§11.2.3) | Hermes cron jobs with `--workdir` = project root and `--skill` (definitions in `config/schedules.yaml`, not installed) | docs `cron.md`: workdir loads AGENTS.md + trusted project skills |
| Deterministic rules (§4.3 of each role) | `bin/hcb` (Python, `hcb/`): thresholds, C1-C11, Top 5, number map, follow-up, verdict gates, envelopes, idempotency, page count | `tests/` (40+ tests) |
| A-H evaluator (TV-05) | `hcb/ah_adapter.py` imports the original `evaluator.py`; inference through an isolated `hermes chat --oneshot -t todo` call | Contract test re-validates the real Glenorchy assessment (59/100) |
| Job Application Engine (TV-04) | `hcb/engine.py` runs the Engine's own `select_evidence.py`, `fit.py`, `verify.py`, `ats_check.py`, `keyword_check.py` against a work folder in `applications/` | Pipeline replay: all checks pass, Engine fingerprint unchanged |
| Baserow (TV-06) | `hcb/baserow.py`, mapped to the live schema of table 839 | Live read + schema-drift test pass; writes dry-run |
| Telegram (TV-08) | Hermes gateway Telegram platform (no custom adapter); PM replies carry `MEDIA:/path` lines for native file delivery; commands parsed by `hcb/commands.py` | Parser tested; live channel pending bot token |
| The user Writing Voice | Project skill `candidate-writing-voice` (controlled copy) | Indexed in RT-01 |
| Secrets (§9.3) | Existing protected token file; never in repo/config/instructions; secret-scan test | `tests/test_contracts_security.py` |
| Untrusted content (§13.6) | Rule in `AGENTS.md` + every skill; A-H inference with a minimal toolset; injection line planted in the test ad | RT-02 |

## 2. Alternatives considered and rejected

| Option | Why not (now) |
|---|---|
| Five Hermes profiles (one per role) | Profiles are separate homes (config, memory, sessions, cron) and are not a sandbox (Master §11.1). They would duplicate config and need `advanced-delegation` routing. Delegation + skills preserves contracts with far less surface. Revisit only if a role needs different model/toolsets (TV-02/TV-03) |
| `advanced-delegation` plugin | Not needed for v1; installing plugins needs approval (Master §11.5) |
| Copying the role specs into five SOUL.md files | SOUL.md is global identity only; it never loads per project. The spec's §0 cores live in the skills instead |
| Copying Engine facts into the project | Would create a second, drifting fact source (Master §2.1) |
| Reimplementing A-H scoring | Forbidden (Master §6.3); original validator reused |
| New MCP server for Baserow | A 200-line adapter on the existing token is smaller, keeps loopback-only and table-839-only guards |

## 3. Reconciliation of sources (conflicts and resolutions)

| # | Conflict | Resolution |
|---|---|---|
| R-01 | Specs cite KB v2.0 (2026-11-12, "R2"); only KB v1.0 (2026-11-07) exists | Use v1.0 + the approved tables in `job-hunter.md` §3.5-3.6, §5.3 (zones, sources, exclusions). Flag in `config/sources.yaml`; Research Agent reports it |
| R-02 | Master §2.3 says evaluator/Baserow locations unknown | Found and verified: evaluator `~/CareerDevelopmentOS/hermes2/job-evaluator`, Baserow `localhost:8080` table 839 |
| R-03 | Specs require Status values Exploratoria / Pendiente de revisión / Cerrada; table 839 has none of them (and no fit/category fields) | User decision 2026-11-13: Notes tag block + migration proposal MIG-01 (`config/baserow-mapping.yaml`). `Withdrawn` is NOT reused for Cerrada (different meaning) |
| R-04 | `candidate-writing-voice` says "normally two variants"; `writer.md` D-WR-04 (newer) says one version per round in this pipeline | Writer spec prevails inside Career Buddy; two variants only on a `Cambios` request asking for options (PROVENANCE.md) |
| R-05 | Engine `voice/` files vs `candidate-writing-voice` | Engine voice/anti-slop rules remain enforced by the Engine's own scripts; expression layer = `candidate-writing-voice` (writer.md §3.6) |
| R-06 | Old A-H launcher is pinned to `job-evaluation-001` and a Docker/Codex zero-tool path | Reuse its logic + schema; own evaluation ids; runtime recorded honestly (GAP-AH-01) |
| R-07 | Existing CareerDevelopmentOS Baserow rules: "no update/delete operations" | That rule governed the earlier pilot. Career Buddy needs updates (Cerrada, references) per Master §9.1; implemented as dry-run-by-default with a user-controlled feature flag. No delete exists |
| R-08 | Engine AGENTS.md: instructions in Spanish, content in English | Kept: PM speaks Spanish, documents en-AU |
| R-10 | Master §3.8 / D-PM-05: no normal weekday alerts; Job Hunter Mon-Fri only | **User decision D-USR-01 (2026-11-13) prevails:** Job Hunter runs every day; ONE daily digest of new offers with the ad's phone/contact so the user applies within 24 h and calls the same day himself. The system still never contacts anyone (D-PM-03 unchanged). Implemented in `hcb/daily.py`, `config/system.yaml daily_alert`, PM skill §D0, Job Hunter step 6b, `config/schedules.yaml`. **Updated by D-USR-02 (2026-11-15, AP-19d0bccce02dfb3ac2b94a8c):** back to Monday-Friday as Master §3.8, but 3 runs (07:30, 12:30, 16:30 Hobart); each offer announced once; silent empty runs |
| R-09 | Engine `out/` contains prior real applications | Used only as format models for the Writer; claims always re-derived from `facts/` |

## 4. Trust boundaries

```
User (Telegram / CLI) ──> PM session (Hermes, AGENTS.md + hcb-project-manager)
                            │  bin/hcb (deterministic gates, ledger, approvals)
                            ├─ delegate_task ─> Job Hunter | Research | Writer | Recruiter (fresh contexts)
                            │                        │ read-only ──> Job Application Engine (fingerprinted)
                            │                        │ read-only ──> A-H evaluator code (imported)
                            ├─ hcb/baserow.py ──> Baserow localhost:8080, table 839 only (writes OFF)
                            └─ files ──> applications/, reports/, state/ (inside project only)
Untrusted: job ads, web pages, documents, subagent outputs (data, never instructions)
```
