# Deployment: the project is built to run on a VPS (Hostinger), with Hermes

The Mac is the build and test machine; the target is a Linux VPS (the user, 2026-11-17 and 2026-11-19).
The move itself waits for the user's approval of a migration plan. Everything below is kept current so the
move is a checklist, not a project.

## Everything the system needs, and where it lives
| Item | Today (Mac) | On the VPS |
|---|---|---|
| Code, skills, method, docs, tests | this folder (git) | `git clone`; set `HCB_ROOT` to the clone path |
| Personal data, packages, audit trail, archives | `private/` (gitignored) | restore from the encrypted backup (`bin/hcb backup`), never via git |
| Hermes profile `career-buddy` (config, Telegram token, allowlist, memory, cron jobs) | `~/.hermes/profiles/career-buddy/` | `hermes profile create career-buddy`; `terminal.cwd` = project; secrets typed again by the user |
| Messaging gateway | launchd service (`~/Library/LaunchAgents/ai.hermes.gateway.plist`, wrapped in `/usr/bin/osascript` for macOS network permission) | `hermes gateway install --system` (systemd); no osascript |
| Baserow | Docker container `baserow` (all-in-one 2.4.1), volume `baserow_data` | same container on the VPS; restore DB (`pg_restore`) and media from the backup; or rebuild empty with the schema below |
| Baserow schema | Applications v2 (P-6), Documents + Contacts + networking (P-7) | `bin/hcb baserow migrate-schema` (preview) / `--apply` builds every missing field and option in the three tables (table ids in `config/baserow-mapping.yaml`; a restored backup keeps them) |
| Baserow token | `~/.hermes/career-buddy/secrets/baserow-token` (700/600) | same path; Create + Update on Applications, Documents, Contacts; never Delete |
| Backup key | `~/.hermes/career-buddy/secrets/backup.key` | same path; **also in the user's password manager** |
| Schedules (Hermes cron, profile career-buddy) | weekday search `aa639c87a2bb`, Friday `8f98c9127775`, Saturday `ea20eb1adf2a`, daily backup `3e3e37b0ac1e` (script `deploy/daily-backup.sh`) | recreate from `config/schedules.yaml` + `deploy/daily-backup.sh` with `--workdir` = project |
| Telegram delivery | `hermes send` from the career-buddy profile (`bin/hcb daily-send`, `report-send`) | unchanged |
| PDF render | Chrome (macOS path) found by `hcb/report.py` and `engine/build/fit.py` | Chromium on Linux, auto-detected (`HCB_CHROME` overrides) |
| PDF text check (ATS) | `pdftotext` if installed, else `swift` (macOS) | install `poppler-utils` (`pdftotext`) |
| Python | Hermes venv (jsonschema, ruamel) + `/usr/bin/python3` with PyYAML for the engine scripts | `python3-yaml`, Hermes install |
| Node | `engine/build/node_modules` | `npm ci` in `engine/build` |
| Docker CLI | `~/.docker/bin/docker` (config `backup.docker`) | `/usr/bin/docker`, auto-detected |
| Power / sleep | Mac must stay on AC (`pmset -c sleep 0`); on battery runs are delayed | not applicable (VPS always on) |

## Before the move (to do)
- Off-site copy of the backups: on the VPS the backup must leave the server (provider snapshot, object storage
  or a pull from the Mac). Deferred by the user until the system is finished.
- Test on the VPS, in order: restore the backup, full test suite (`HCB_PRIVATE_DIR` real and demo), Engine
  selftest, one manual search, one Telegram digest; only then install the schedules.
