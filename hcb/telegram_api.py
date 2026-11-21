"""Send one Telegram message with an inline keyboard (P-10 `Prepare Docs` buttons). No LLM.

`hermes send` cannot attach buttons, so this calls the Bot API directly with the career-buddy profile's own
bot token and home chat (read from that profile's .env, never printed or logged). Button taps are handled
inside the Hermes gateway by the `career-buddy-buttons` plugin (same allowlist as messages).
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

from .util import config


def _profile_env() -> dict:
    prof = (config().get("telegram") or {}).get("profile", "career-buddy")
    env = Path.home() / ".hermes" / "profiles" / prof / ".env"
    out = {}
    for line in env.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*(TELEGRAM_BOT_TOKEN|TELEGRAM_HOME_CHANNEL)\s*=\s*(.+?)\s*$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip("'\"")
    return out


def send_message(text: str, keyboard: list[list[dict]], api=None) -> tuple[bool, str | None, str | None]:
    """Returns (ok, message_id, error), like daily.hermes_send."""
    import sys
    if api is None and ("unittest" in sys.modules or os.environ.get("HCB_NO_LIVE_WRITES")):
        return False, None, "test run: real Telegram sends are disabled"      # 2026-11-20: tests sent real messages
    env = _profile_env()
    token, chat = env.get("TELEGRAM_BOT_TOKEN"), env.get("TELEGRAM_HOME_CHANNEL")
    if not token or not chat:
        return False, None, "telegram token or home channel missing in the profile .env"
    for row in keyboard:
        for b in row:
            if len(b["callback_data"].encode()) > 64 or not b["callback_data"].startswith("hcb:"):
                return False, None, f"invalid callback_data {b['callback_data']!r}"
    body = {"chat_id": chat, "text": text[:4096], "disable_web_page_preview": True,
            "reply_markup": {"inline_keyboard": keyboard}}
    if api:
        res = api(body)
    else:
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                     data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return False, None, f"Telegram HTTP {e.code}"
        except urllib.error.URLError as e:
            return False, None, f"Telegram unreachable: {e.reason}"
    if res.get("ok"):
        return True, str(res["result"]["message_id"]), None
    return False, None, str(res.get("description") or "send failed")[:200]
