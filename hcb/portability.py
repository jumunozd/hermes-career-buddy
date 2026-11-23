"""Migration readiness (`bin/hcb doctor --deploy`). No LLM, read-only, never reads a secret's content.

Lists every runtime dependency the system needs, whether this machine has it, and the fix on a Linux VPS
(docs/DEPLOYMENT.md). Run it on the Mac before the move and again on the VPS after `git clone` + restore:
the move is done when every line is ok.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .util import ROOT, authority_path, config, private_dir

SECRETS = Path("~/.hermes/career-buddy/secrets").expanduser()


def _py_has(py: str, *mods: str) -> bool:
    try:
        r = subprocess.run([py, "-c", "import " + ",".join(mods)], capture_output=True, timeout=30, cwd="/")
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _secret(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    mode = path.stat().st_mode & 0o777
    return (mode & 0o077) == 0, f"present, mode {oct(mode)}"


def _hermes_profile() -> Path:
    prof = (config().get("telegram") or {}).get("profile", "career-buddy")
    return Path.home() / ".hermes" / "profiles" / prof


def checks() -> list[dict]:
    from . import engine, report
    out = []

    def add(item, ok, detail, vps):
        out.append({"item": item, "ok": bool(ok), "detail": detail, "on_vps": vps})

    add("python modules (jsonschema, ruamel.yaml)", _py_has(sys.executable, "jsonschema", "ruamel.yaml"),
        sys.executable, "pip install -r requirements.txt in the Hermes venv")
    add("PDF reader for user ads (pypdf, or pdftotext)",
        _py_has(sys.executable, "pypdf") or shutil.which("pdftotext") or _py_has("/usr/bin/python3", "fitz"),
        "pypdf" if _py_has(sys.executable, "pypdf") else "pdftotext" if shutil.which("pdftotext")
        else "macOS PyMuPDF only", "pip install pypdf (requirements.txt) or apt install poppler-utils")
    epy = engine.ENGINE_PY
    add("Engine python with PyYAML", _py_has(epy, "yaml"), epy, "apt install python3-yaml (or set HCB_ENGINE_PY)")
    add("Chrome/Chromium for PDF render", Path(report.CHROME).exists(), report.CHROME,
        "apt install chromium (auto-detected; HCB_CHROME overrides)")
    add("PDF text check for ATS (pdftotext or swift)", shutil.which("pdftotext") or shutil.which("swift"),
        "pdftotext" if shutil.which("pdftotext") else "swift (macOS only)" if shutil.which("swift") else "none",
        "apt install poppler-utils")
    nm = ROOT / "engine" / "build" / "node_modules"
    add("Node modules for the DOCX build", nm.is_dir() and shutil.which("node"), str(nm.relative_to(ROOT)),
        "apt install nodejs npm; npm ci in engine/build")
    add("hermes CLI", shutil.which("hermes"), shutil.which("hermes") or "not on PATH", "install Hermes Agent")
    prof = _hermes_profile()
    add("Hermes profile", (prof / "config.yaml").is_file(), str(prof).replace(str(Path.home()), "~"),
        "hermes profile create career-buddy; terminal.cwd = project")
    plug = prof / "plugins" / "career-buddy-buttons" / "__init__.py"
    add("Telegram buttons plugin deployed", plug.is_file(), "deploy/hermes-plugin/career-buddy-buttons",
        "copy deploy/hermes-plugin/career-buddy-buttons into the profile's plugins/")
    try:
        jobs = json.loads((prof / "cron" / "jobs.json").read_text(encoding="utf-8"))
        jobs = jobs.get("jobs", jobs) if isinstance(jobs, dict) else jobs
        n = len(jobs)
    except (OSError, ValueError):
        n = 0
    add("Scheduled jobs (Hermes cron)", n >= 4, f"{n} jobs", "recreate from config/schedules.yaml + deploy/daily-backup.sh")
    env = prof / ".env"
    add("Telegram token in the profile .env (not read)", env.is_file(), "present" if env.is_file() else "missing",
        "the user types it again in the profile .env")
    for name, path, vps in (
            ("Baserow token", authority_path("baserow_token_file"), "same path, chmod 600 (Create + Update only)"),
            ("Backup key", SECRETS / "backup.key", "same path, chmod 600; also in the password manager"),
            ("iCloud app password", Path(os.path.expanduser(_mailbox().get("app_password_file")
                                                               or SECRETS / "icloud-app-password")),
             "same path, chmod 600 (or a new app-specific password)")):
        ok, detail = _secret(path)
        add(f"{name} (not read)", ok, detail, vps)
    add("Mailbox config (private/config/alerts-mailbox.yaml)", bool(_mailbox()), "present" if _mailbox() else "missing",
        "restored with private/ from the encrypted backup")
    from . import backup
    add("Docker CLI for Baserow + backup", Path(backup._docker()).exists(), backup._docker(),
        "apt install docker; same 'baserow' container, restore pg_dump + media")
    add("Private data zone", (private_dir() / "facts").is_dir(), "private/facts present" if (private_dir() / "facts").is_dir()
        else "missing", "restore private/ from the encrypted backup (never via git)")
    return out


def _mailbox() -> dict:
    from . import mailer
    try:
        return mailer.mailbox()
    except Exception:
        return {}


def summary() -> dict:
    cs = checks()
    return {"ready": all(c["ok"] for c in cs), "ok": sum(c["ok"] for c in cs), "total": len(cs),
            "missing": [c["item"] for c in cs if not c["ok"]], "checks": cs}
