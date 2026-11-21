# Runbook (operation on the Mac)

All commands run from the project root: `cd "$HCB_ROOT"` (the folder you cloned).

## Health check
```bash
bin/hcb doctor                      # paths, Engine fingerprint, A-H import + pins, flags, skills
bin/hcb baserow schema-check        # live table 839 equals config/baserow-mapping.yaml
hermes skills list | grep -E "hcb-|juan-"   # 6 project skills, source "project"
```
Tests: `$(ls -d ~/.hermes/installs/*/environments/*/venv/bin/python3 | head -1) -B -m unittest discover -s tests -t .`

## Start / stop
- Interactive: `hermes` (or the desktop app) with the workspace set to this folder. The session is the PM.
- One-off: `hermes chat -Q --oneshot -q "Estado"`.
- Scheduled jobs: none installed. `hermes pause` / `hermes resume` stop/resume ALL cron fires globally.

## Run a workflow manually (safe mode)
- Prepare a test application: `hermes chat -Q --oneshot --query-file tests/fixtures/e2e-prompt.txt`.
- Weekly report from a snapshot JSON: `bin/hcb report <snapshot.json> --date YYYY-MM-DD`.
- A-H on an ad file: `bin/hcb ah run --ad <ad.txt> --state PRELIMINARY --out state/ah/<id>`.

## Approve or reject
User commands (Spanish, via Telegram once configured, or the CLI): `Prepara las ofertas 1,3`,
`Cambios [ID]: ...`, `Elijo A [ID]`, `Aprobado [ID]`, `Enviada [ID] [fecha]`, `Entrevista [ID] [fecha]`,
`Resultado [ID]: rechazo|oferta|retirada|otro`, `Follow-up [ID] sí|no`, `Aprueba propuesta P-n`,
`Pausa`, `Reanuda`, `Estado`, `Cancela [ID]`. Every approval is appended to `state/approvals.jsonl`.

## Find things
| What | Where |
|---|---|
| Application versions | `applications/<opportunity>/<preparation>/vN/` (+ `manifest.json` with hashes) |
| Latest version | highest `vN` with a `manifest.json` (`hcb/engine.py latest_version`) |
| Reports + number map | `reports/<report_id>/report.json` |
| Task envelopes/results | `state/tasks/` |
| Errors, events, approvals, idempotency | `state/events.jsonl`, `state/approvals.jsonl`, `state/ledger.jsonl` |

## Recover an interrupted run without duplicate writes
1. Look up the task in `state/tasks/` and its key in `state/ledger.jsonl`.
2. `applied` → done, do not repeat. `attempted`/`unverified` → read the real Baserow row first
   (`bin/hcb baserow list`), then decide. Never blind-retry an external write.
3. A published version folder is immutable: a rerun creates `vN+1`.

## Credentials
- Baserow token: lives in `~/.hermes/career-buddy/secrets/baserow-token` (dir 700, file 600, outside the
  repository; moved there 2026-11-17). Rotate: revoke in Baserow, delete that file yourself, run the private
  helper `bash ~/CareerDevelopmentOS/baserow-integration/setup-token.sh` (it writes to its own `.secrets/`),
  then move the new file to `~/.hermes/career-buddy/secrets/baserow-token` and run `bin/hcb doctor`. Live writes additionally need `features.baserow_live_writes: true`
  and Create/Update permission on table 839 only.
- Telegram: Hermes profile `career-buddy` owns the bot (`~/.hermes/profiles/career-buddy/.env`: `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_ALLOWED_USERS`; `terminal.cwd` = this folder). The default profile has no Telegram and no career data.
- Never paste tokens into chat, instructions, config or this repository.

## Backup, restore, rollback
### Daily encrypted backup (2026-11-19)
- `bin/hcb backup` (Hermes cron `daily-backup`, 03:00, profile career-buddy; a failure is sent to Telegram):
  one archive `~/.hermes/career-buddy/backups/daily/hcb-backup-<date>.tar.enc` with private/ (tar.gz),
  the Baserow database (`pg_dump -Fc`) and the Baserow uploaded files (media). AES-256 with the key
  `~/.hermes/career-buddy/secrets/backup.key`. **Save that key in your password manager: without it no
  backup can be opened.** Keeps the newest 7 plus one per week for 4 weeks. Verified on every run.
- Off-disk copies: add a folder to `backup.extra_destinations` in config/system.yaml (external drive or
  iCloud Drive); the archive is already encrypted.
- Restore: `openssl enc -d -aes-256-cbc -pbkdf2 -in <archive> -out b.tar -pass file:~/.hermes/career-buddy/secrets/backup.key`,
  `tar -xf b.tar`; `tar -xzf private.tar.gz` into the project folder; Baserow: `docker exec -i baserow sh -c
  'cat > /tmp/r.dump && su postgres -c "pg_restore --clean -d baserow /tmp/r.dump"' < baserow-db.dump` and
  copy `baserow-media.tar` back into `/baserow/data/`. Restore test passed 2026-11-19 (facts and applications
  identical; database restored into a scratch DB).

- Instructions/config/code: this git repository (`git log`, `git revert`). Skills are versioned in frontmatter.
- Generated documents and state: copy `applications/`, `reports/`, `state/` (git-ignored, personal data).
- Undo the Hermes change made for this project: `hermes skills untrust "$HCB_ROOT"`.
- VPS migration: out of scope until local acceptance (Master §15 Fase 6).
