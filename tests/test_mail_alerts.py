"""Job-alert e-mails (P-3 + P-12 D-P12-1): allowlisted senders only, card text only, read-only, no links opened."""
import re
import tempfile
import unittest
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from unittest import mock

from hcb import mailalerts, util

NOW = datetime.fromisoformat("2026-11-24T12:30:00+11:00")
SEEK_TEXT = """Hi Jane, we've got new jobs for you
[image: logo]
Continuous Improvement Coordinator
Acme Foods
Launceston, Launceston & North East TAS

   - Permanent, full-time position
   - Supportive team

<https://email.s.seek.com.au/uni/ss/c/AAA111/h1>
[image: logo]
Senior Process Engineer
Acme Metals
Hobart TAS
$150,000 - $170,000 per year

   - Lead a team

<https://email.s.seek.com.au/uni/ss/c/BBB222/h2>
[image: logo]
Project Officer
Example Council
Perth WA

<https://email.s.seek.com.au/uni/ss/c/CCC333/h3>
View more jobs
<https://email.s.seek.com.au/uni/ss/c/DDD444/h5>
Unsubscribe
<https://email.s.seek.com.au/ss/c/EEE555/h15>
"""


def raw(sender="SEEK <noreply@s.seek.com.au>", text=SEEK_TEXT, subject="Continuous Improvement Coordinator + 2 new jobs"):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = sender, "alerts@example.com", subject
    m.set_content(text)
    return m.as_bytes()


class Parse(unittest.TestCase):
    def test_seek_cards(self):
        cards = mailalerts.parse_seek(SEEK_TEXT)
        self.assertEqual([c["title"] for c in cards],
                         ["Continuous Improvement Coordinator", "Senior Process Engineer", "Project Officer"])
        self.assertEqual(cards[0]["company"], "Acme Foods")
        self.assertTrue(cards[0]["location"].startswith("Launceston"))
        self.assertEqual(cards[0]["url"], "https://email.s.seek.com.au/uni/ss/c/AAA111/h1")
        self.assertTrue(cards[1]["salary"].startswith("$150,000"))
        self.assertNotIn("Unsubscribe", " ".join(c["card_text"] for c in cards))

    def test_sender_allowlist(self):
        self.assertEqual(mailalerts.sender_id("SEEK <noreply@s.seek.com.au>"), "seek")
        self.assertIsNone(mailalerts.sender_id("Someone <me@gmail.com>"))           # a forward is not SEEK
        self.assertIsNone(mailalerts.sender_id("x@seek.com.au.evil.com"))
        self.assertEqual(mailalerts.parse_message(raw("Me <me@gmail.com>"))["cards"], [])


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = dict(util.config()); self.cfg["features"] = {**self.cfg["features"], "email_alerts": True}
        self.p = [mock.patch("hcb.mailalerts.config", return_value=self.cfg),
                  mock.patch("hcb.mailalerts.project_path", side_effect=lambda k: Path(self.tmp.name)),
                  mock.patch("hcb.state.project_path", side_effect=lambda k: Path(self.tmp.name))]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()
        self.tmp.cleanup()

    def test_shortlist_card_only_and_seen_next_time(self):
        res = mailalerts.run(NOW, messages=[(1, raw()), (2, raw("Spam <x@other.com>"))])
        self.assertEqual(res["parsed"], 1); self.assertEqual(res["skipped_by_domain"], {"other.com": 1})
        self.assertEqual([s["title"] for s in res["shortlist"]], ["Continuous Improvement Coordinator"])
        item = res["shortlist"][0]
        self.assertFalse(item["read_detail_allowed"]); self.assertEqual(item["channel"], "email_alert")
        self.assertIn("Permanent", item["card_text"])
        self.assertEqual(res["logged_by_title"] + res["out_of_zone"], 2)          # Senior excluded, Perth out of zone
        self.assertFalse(item["card_text"].endswith("<"))
        # like the listing sweep: excluded cards are logged at once; shortlisted ones when the Job Hunter decides
        again = mailalerts.run(NOW, messages=[(3, raw())])                          # same alert repeated
        self.assertEqual(again["known_unchanged"], 2); self.assertEqual(len(again["shortlist"]), 1)

    def test_switch_off_and_test_guard(self):
        self.cfg["features"]["email_alerts"] = False
        self.assertIn("false", mailalerts.run(NOW, messages=[(1, raw())])["skipped"])
        self.cfg["features"]["email_alerts"] = True
        self.assertIn("test run", mailalerts.run(NOW)["skipped"])                  # no real mailbox under tests

    def test_read_only_mailbox(self):
        class FakeImap:
            def __init__(s): s.calls = []
            def select(s, box, readonly=False): s.calls.append(("select", readonly)); return "OK", [b"2"]
            def response(s, code): return code, [b"7"]
            def uid(s, cmd, *args):
                s.calls.append((cmd, args))
                if cmd == "SEARCH":
                    return "OK", [b"1 2"]
                return "OK", [(b"1 (BODY[] {10}", raw())]
            def logout(s): pass
        imap = FakeImap()
        with mock.patch("hcb.mailer.mailbox", return_value={"primary_address": "me@example.com"}):
            res = mailalerts.run(NOW, imap=imap)
        self.assertEqual(res["messages"], 2)
        self.assertIn(("select", True), imap.calls)                                 # EXAMINE, never SELECT
        self.assertTrue(all("PEEK" in a[1] for c, a in imap.calls if c == "FETCH"))  # stays unread
        self.assertEqual(mailalerts._load_state()["last_uid"], 2)

    def test_no_write_or_link_code(self):
        src = Path(mailalerts.__file__).read_text()
        for bad in ("STORE", "COPY", "MOVE", "EXPUNGE", ".delete(", "urlopen", "requests", "webbrowser"):
            self.assertNotIn(bad, src, bad)


if __name__ == "__main__":
    unittest.main()
