"""E-mail delivery (P-10 D-P10-2/3): only to the user's own address, once per key, never from tests."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from hcb import delivery, mailer, report, util

BOX = {"primary_address": "me@example.com", "app_password_file": "/nonexistent"}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = dict(util.config())
        self.cfg["features"] = {**self.cfg["features"], "email_delivery": True, "telegram_delivery": True}
        self.patches = [mock.patch("hcb.mailer.config", return_value=self.cfg),
                        mock.patch("hcb.mailer.mailbox", return_value=BOX),
                        mock.patch("hcb.mailer.project_path", side_effect=lambda k: Path(self.tmp.name)),
                        mock.patch("hcb.state.project_path", side_effect=lambda k: Path(self.tmp.name))]
        for p in self.patches:
            p.start()
        self.sent = []

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def smtp(self, msg):
        self.sent.append(msg)


class Mailer(Base):
    def test_sends_once_per_key_to_the_user_only(self):
        first = mailer.send("k1", "Subject", "Body", smtp=self.smtp)
        again = mailer.send("k1", "Subject", "Body", smtp=self.smtp)
        forced = mailer.send("k1", "Subject", "Body", smtp=self.smtp, resend=True)
        self.assertEqual([first["status"], again["status"], forced["status"]], ["sent", "already", "sent"])
        self.assertEqual(len(self.sent), 2)
        self.assertEqual(self.sent[0]["To"], "me@example.com")
        self.assertIsNone(self.sent[0]["Cc"]); self.assertIsNone(self.sent[0]["Bcc"])

    def test_recipient_outside_allowlist_is_refused(self):
        real = mailer.build
        with mock.patch("hcb.mailer.build", side_effect=lambda *a, **k: real(*a, to="someone@else.com")):
            res = mailer.send("k2", "S", "B", smtp=self.smtp)
        self.assertEqual(res["status"], "not_sent"); self.assertEqual(self.sent, [])

    def test_switch_off_and_test_guard(self):
        self.cfg["features"]["email_delivery"] = False
        self.assertEqual(mailer.send("k3", "S", "B", smtp=self.smtp)["status"], "not_sent")
        self.cfg["features"]["email_delivery"] = True
        res = mailer.send("k4", "S", "B")                      # no fake SMTP: a real send is refused under tests
        self.assertEqual(res["status"], "not_sent"); self.assertIn("test run", res["reason"])

    def test_no_mailbox_configured(self):
        with mock.patch("hcb.mailer.mailbox", return_value={}):
            self.assertEqual(mailer.send("k5", "S", "B", smtp=self.smtp)["status"], "not_sent")


class Package(Base):
    def _version(self, ready=True):
        prep = Path(self.tmp.name) / "app" / "prep-1"
        v = prep / "v1"; v.mkdir(parents=True)
        (v / "manifest.json").write_text(json.dumps({"version_id": "PREP-1-v1", "version_label": "v1", "opportunity_ref": "1"}))
        (v / "content.json").write_text(json.dumps({"application": "Acme Water, Asset Officer (Hobart)"}))
        for f in ("cv-juan-munoz.pdf", "cv-juan-munoz.docx", "cover-letter.pdf", "cover-letter.docx"):
            (v / f).write_bytes(b"x")
        (v / "missing-fact-requests.json").write_text(json.dumps([{"claim_needed": "Add a scheduling case."}]))
        (prep / "recruiter-review-v1-r1.json").write_text(json.dumps(
            {"verdict": "Pasa a entrevista", "round": 1,
             "send_readiness": "ready_for_human_review" if ready else "not_fit_to_send"}))
        return v

    def test_split_application(self):
        self.assertEqual(delivery.split_application("TasPorts, Project Controls Officer (Hobart or Launceston)"),
                         ("Project Controls Officer", "TasPorts"))
        self.assertEqual(delivery.split_application("Shaw Contracting (Aust) Pty Ltd, BD Support Officer (Launceston)")[0],
                         "BD Support Officer")

    def _shown(self, ready=True):
        v = self._version(ready)
        shown = delivery.show(v)
        self.assertEqual(shown["status"], "shown")
        return v, shown

    def test_ready_package(self):
        v, _ = self._shown()
        res = delivery.send_package(v, fit="B, recomendable", smtp=self.smtp, confirmed="Correo 1")
        self.assertEqual(res["status"], "sent", res); self.assertTrue(res["ready"])
        msg = self.sent[0]
        self.assertEqual(msg["Subject"], "Application Ready: Asset Officer | Acme Water")
        names = [p.get_filename() for p in msg.iter_attachments()]
        self.assertEqual(names, ["cv-juan-munoz.pdf", "cover-letter.pdf"])     # every document, as PDF
        body = msg.get_body(("plain",)).get_content()
        self.assertIn("Fit A-H: B, recomendable", body); self.assertIn("Add a scheduling case.", body)
        self.assertIn("nunca envía postulaciones", body)
        self.assertNotIn("—", msg["Subject"] + body)        # no em dashes anywhere

    def test_docx_only_when_asked(self):
        v, _ = self._shown()
        delivery.send_package(v, smtp=self.smtp, confirmed="Correo 1", with_docx=True)
        self.assertEqual(len(list(self.sent[0].iter_attachments())), 4)

    def test_telegram_review_shows_every_pdf(self):
        _, shown = self._shown()
        self.assertEqual(shown["files"], ["cv-juan-munoz.pdf", "cover-letter.pdf"])
        self.assertEqual(shown["media_lines"].count("MEDIA:"), 2)
        self.assertIn("Correo 1", shown["ask_user"])

    def test_no_email_before_telegram_review_and_confirmation(self):
        v = self._version()
        res = delivery.send_package(v, smtp=self.smtp, confirmed="Correo 1")
        self.assertEqual(res["status"], "not_sent"); self.assertIn("Telegram", res["reason"])
        delivery.show(v)
        for msg in (None, "Aprobado 1", "Prepara la oferta 1"):
            self.assertEqual(delivery.send_package(v, smtp=self.smtp, confirmed=msg)["status"], "not_sent")
        self.assertEqual(self.sent, [])
        self.assertEqual(delivery.send_package(v, smtp=self.smtp, confirmed="Mándalo a mi correo")["status"], "sent")

    def test_confirmation_for_another_offer_is_refused(self):
        v, _ = self._shown()
        self.assertEqual(delivery.send_package(v, smtp=self.smtp, confirmed="Correo 99")["status"], "not_sent")

    def test_document_without_pdf_is_refused(self):
        v = self._version()
        (v / "cover-letter.pdf").unlink()
        self.assertIn("cover-letter", delivery.show(v)["reason"])

    def test_not_fit_package_is_marked_draft(self):
        v, _ = self._shown(ready=False)
        res = delivery.send_package(v, smtp=self.smtp, confirmed="Correo 1")
        self.assertFalse(res["ready"]); self.assertTrue(self.sent[0]["Subject"].startswith("Application Draft"))

    def test_unpublished_folder_is_refused(self):
        v = Path(self.tmp.name) / "draft"; v.mkdir()
        self.assertEqual(delivery.send_package(v, smtp=self.smtp)["status"], "not_sent")


class WeeklyReport(Base):
    def test_pdf_by_email_and_short_telegram_notice(self):
        d = Path(self.tmp.name) / "R-X"; d.mkdir()
        (d / "report.pdf").write_bytes(b"%PDF")
        (d / "report.json").write_text(json.dumps({"report_id": "R-X", "top5": [1], "exploratory": [], "followups_recommended": [],
                                                  "within_limit": True, "page_count": 2,
                                                  "files": {"pdf": str(d / "report.pdf")}, "delivery": None}))
        tg = []
        run = lambda c: tg.append(Path(c[-1]).read_text()) or SimpleNamespace(returncode=0, stdout='{"message_id": "7"}', stderr="")
        with mock.patch("hcb.report.config", return_value=self.cfg), mock.patch("hcb.daily.config", return_value=self.cfg), \
             mock.patch("hcb.report.project_path", side_effect=lambda k: Path(self.tmp.name)):
            res = report.send("R-X", runner=run, smtp=self.smtp)
        self.assertEqual(res["status"], "delivered"); self.assertEqual(res["email"]["status"], "sent")
        self.assertEqual(len(self.sent), 1); self.assertNotIn("MEDIA:", tg[0]); self.assertIn("correo", tg[0])


if __name__ == "__main__":
    unittest.main()
