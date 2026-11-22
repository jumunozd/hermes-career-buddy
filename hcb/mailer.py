"""E-mail delivery to the user (P-10 D-P10-2, D-P10-3). No LLM.

Plain SMTP over TLS from the user's dedicated iCloud mailbox. The address lives in
private/config/alerts-mailbox.yaml (never in git); the app-specific password in a 0600 file outside the
project (never read into logs or output). Hard rules:
- the only possible recipient is the user's own address (recipient allowlist, no CC/BCC);
- feature flag `features.email_delivery`;
- real sends are refused while tests run;
- each delivery key is sent once (state/email-deliveries.jsonl), unless resend is asked explicitly.
"""
from __future__ import annotations

import json
import mimetypes
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

from . import state
from .util import config, load_yaml, now_iso, private_dir, project_path

SMTP_HOST, SMTP_PORT = "smtp.mail.me.com", 587
MAX_ATTACH_BYTES = 15 * 1024 * 1024          # iCloud accepts 20 MB per message; keep a margin
LOG = "email-deliveries.jsonl"


def mailbox() -> dict:
    """{'primary_address', 'app_password_file', ...} or {} when not configured (demo persona, new install)."""
    p = private_dir() / "config" / "alerts-mailbox.yaml"
    try:
        return load_yaml(p) or {}
    except FileNotFoundError:
        return {}


def allowed_recipients() -> set[str]:
    addr = (mailbox().get("primary_address") or "").strip().lower()
    return {addr} if addr else set()


def _password() -> str:
    f = Path(os.path.expanduser(mailbox().get("app_password_file")
                                or "~/.hermes/career-buddy/secrets/icloud-app-password"))
    if f.stat().st_mode & 0o077:
        raise PermissionError("the app password file must be readable only by its owner (chmod 600)")
    return f.read_text(encoding="utf-8").strip()


def already_sent(key: str) -> dict | None:
    p = project_path("state") / LOG
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("key") == key and r.get("status") == "sent":
            return r
    return None


def build(subject: str, body: str, attachments: list[Path] = (), to: str | None = None) -> EmailMessage:
    box = mailbox()
    sender = box.get("primary_address")
    to = (to or sender or "").strip()
    msg = EmailMessage()
    msg["From"] = f"Hermes Career Buddy <{sender}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="career-buddy.local")
    msg.set_content(body)
    total = 0
    for a in attachments:
        a = Path(a)
        data = a.read_bytes()
        total += len(data)
        ctype, _ = mimetypes.guess_type(a.name)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=a.name)
    if total > MAX_ATTACH_BYTES:
        raise ValueError(f"attachments total {total} bytes, over the {MAX_ATTACH_BYTES} byte limit")
    return msg


def send(key: str, subject: str, body: str, attachments: list[Path] = (), what: str = "email",
         resend: bool = False, smtp=None, dry_run: bool = False, require_flag: bool = True) -> dict:
    """Send one e-mail to the user. Returns {'status': sent|already|not_sent|failed|dry_run, ...}.
    require_flag=False only for `bin/hcb mail-test` (the check that runs before the flag is turned on)."""
    if require_flag and not config()["features"].get("email_delivery") and not dry_run:
        return {"status": "not_sent", "reason": "features.email_delivery is false"}
    allow = allowed_recipients()
    if not allow:
        return {"status": "not_sent", "reason": "no mailbox configured in private/config/alerts-mailbox.yaml"}
    if not resend and (prev := already_sent(key)):
        return {"status": "already", "at": prev.get("at")}
    try:
        msg = build(subject, body, attachments)
    except (OSError, ValueError) as e:
        return {"status": "not_sent", "reason": str(e)[:300]}
    rcpts = {msg["To"].strip().lower()}
    if not rcpts <= allow or msg["Cc"] or msg["Bcc"]:
        return {"status": "not_sent", "reason": "recipient outside the allowlist"}
    info = {"subject": subject, "attachments": [Path(a).name for a in attachments]}
    if dry_run:
        return {"status": "dry_run", **info, "bytes": len(msg.as_bytes())}
    if smtp is None and ("unittest" in sys.modules or os.environ.get("HCB_NO_LIVE_WRITES")):
        return {"status": "not_sent", "reason": "test run: real e-mail sends are disabled"}
    try:
        if smtp is not None:
            smtp(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(mailbox()["primary_address"], _password())
                s.send_message(msg, to_addrs=list(rcpts))
        status, err = "sent", None
    except (OSError, smtplib.SMTPException) as e:
        status, err = "failed", f"{type(e).__name__}: {str(e)[:200]}"
    rec = {"key": key, "what": what, "status": status, "at": now_iso(), **info}
    if err:
        rec["error"] = err
    state._append(LOG, rec)
    state.event("delivery", what=what, channel="email", status=status, key=key)
    return {k: v for k, v in rec.items() if k != "key"}
