"""career-buddy-buttons: Telegram `Prepare Docs` buttons of the Hermes Career Buddy daily digest (P-10).

Callback data `hcb:prep:<Baserow row id | o-xxxxxx>`. On a tap:
1. the tapper must pass the bot's normal allowlist (the same gate as messages and core buttons);
2. `bin/hcb prepare-request --ref <id>` records the request once (a second tap starts nothing new) and marks
   the Baserow row `Preparing`;
3. the tap is answered ("Document preparation started" / "Already requested");
4. a new request is handed to the Project Manager as the user's own instruction `Prepara la oferta <id>`
   (exactly what typing it would do: same approval rules, preparation only, never send or contact).
Registered in its own handler group so the core catch-all callback handler is not shadowed.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re

logger = logging.getLogger(__name__)
PATTERN = r"^hcb:prep:(\d{1,9}|o-[0-9a-f]{6})$"
HCB_ROOT = os.environ.get("HCB_ROOT") or os.path.expanduser("~/Desktop/Hermes Career Buddy")


def register(ctx) -> None:
    ctx.register_telegram_handler(_factory)


def _factory(native, adapter) -> None:
    from telegram.ext import CallbackQueryHandler

    async def on_tap(update, context):
        await _on_tap(update, adapter)

    native.add_handler(CallbackQueryHandler(on_tap, pattern=PATTERN), group=-7)


async def _run_hcb(ref: str, user_id: str) -> dict:
    proc = await asyncio.create_subprocess_exec(
        os.path.join(HCB_ROOT, "bin", "hcb"), "prepare-request", "--ref", ref, "--user", user_id,
        cwd=HCB_ROOT, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await asyncio.wait_for(proc.communicate(), timeout=120)
    text = out.decode(errors="ignore")
    start = text.find("{")
    if proc.returncode != 0 or start < 0:
        return {"status": "error", "reason": (err.decode(errors="ignore") or text)[-200:]}
    return json.loads(text[start:])


async def _confirm(query, res: dict) -> None:
    text = res.get("confirmation")
    if text and query.message is not None:
        try:
            await query.message.reply_text(text)
        except Exception as exc:
            logger.warning("career-buddy-buttons: confirmation not sent: %s", exc)


async def _on_tap(update, adapter) -> None:
    query = update.callback_query
    m = re.match(PATTERN, (query.data or "") if query else "")
    if not m:
        return
    ref = m.group(1)
    cb = adapter._callback_ctx(query)
    if not await adapter._callback_authorized(query, cb, "Not authorised."):
        logger.warning("career-buddy-buttons: refused tap from user %s", getattr(query.from_user, "id", "?"))
        return
    user_id = str(getattr(query.from_user, "id", ""))
    try:
        res = await _run_hcb(ref, user_id)
    except Exception as exc:  # never crash the gateway on a button
        logger.error("career-buddy-buttons: prepare-request failed: %s", exc)
        await query.answer(text="Could not start: try «Prepara la oferta %s»." % ref)
        return
    status = res.get("status")
    if status == "test":
        await query.answer(text="Test OK: the Prepare Docs button works (nothing was started).")
        await _confirm(query, res)
        return
    if status == "already_requested":
        await query.answer(text="Already requested: document preparation is in progress.")
        await _confirm(query, res)
        return
    if status != "started":
        await query.answer(text="Could not start (%s). Try «Prepara la oferta %s»." % (status, ref))
        return
    await query.answer(text="Document preparation started")
    await _confirm(query, res)                    # the user, 2026-11-20: a text confirmation in the chat
    # Hand the PM the same instruction the user would type.
    from gateway.platforms.event import MessageEvent, MessageType
    msg = query.message
    source = adapter.build_source(
        chat_id=str(msg.chat_id), chat_name=None, chat_type="dm", user_id=user_id,
        user_name=getattr(query.from_user, "full_name", None), message_id=str(msg.message_id))
    event = MessageEvent(text=res.get("instruction") or f"Prepara la oferta {ref}", message_type=MessageType.TEXT,
                         source=source, message_id=f"hcbprep-{query.id}")
    await adapter.handle_message(event)
