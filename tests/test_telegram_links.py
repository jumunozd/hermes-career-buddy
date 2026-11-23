"""Long portal links become a short clickable label in Telegram (the user, 2026-11-23)."""
import unittest
from unittest import mock

from hcb import telegram_api

SEEK = "https://email.s.seek.com.au/uni/ss/c/" + "x" * 300 + "/h1/h001.abc"


class Linkify(unittest.TestCase):
    def test_long_seek_link_gets_a_label(self):
        text = f"🏆 TOP 3\n1. Project Manager Assistant – Acme\n   🔗 {SEEK}\n   📎 Aviso"
        out, ents = telegram_api.linkify(text)
        self.assertNotIn(SEEK, out); self.assertIn("🔗 Abrir aviso en SEEK", out)
        e = ents[0]
        self.assertEqual(e["url"], SEEK)
        u16 = out.encode("utf-16-le")
        self.assertEqual(u16[e["offset"] * 2:(e["offset"] + e["length"]) * 2].decode("utf-16-le"), "Abrir aviso en SEEK")

    def test_short_link_stays_visible(self):
        out, ents = telegram_api.linkify("🔗 https://www.tasports.com.au/careers")
        self.assertIn("tasports.com.au/careers", out); self.assertEqual(ents, [])

    def test_send_uses_entities(self):
        sent = []
        with mock.patch("hcb.telegram_api._profile_env", return_value={"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_HOME_CHANNEL": "1"}):
            ok, ref, err = telegram_api.send_message(f"🔗 {SEEK}", [[{"text": "b", "callback_data": "hcb:prep:1"}]],
                                                     api=lambda b: sent.append(b) or {"ok": True, "result": {"message_id": 5}})
        self.assertTrue(ok); self.assertEqual(sent[0]["text"], "🔗 Abrir aviso en SEEK")
        self.assertEqual(sent[0]["entities"][0]["type"], "text_link")


if __name__ == "__main__":
    unittest.main()
