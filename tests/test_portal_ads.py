"""Portal ads (the user, 2026-11-22): offers from alert e-mails or SEEK/LinkedIn/Indeed links are prepared only
from the full ad the user sends (PDF or text); the system never opens the portal page."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from hcb import adsource, commands, daily, prepare_request

AD = "Project Officer\nAcme Water\nHobart TAS\n\nAbout the role\n" + ("You will coordinate capital works projects. " * 20)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = [mock.patch("hcb.adsource.project_path", side_effect=lambda k: Path(self.tmp.name)),
                  mock.patch("hcb.state.project_path", side_effect=lambda k: Path(self.tmp.name))]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()
        self.tmp.cleanup()


class AdSource(Base):
    def test_portal_hosts(self):
        for u in ("https://www.seek.com.au/job/123", "https://email.s.seek.com.au/uni/ss/c/abc",
                  "https://au.linkedin.com/jobs/view/1", "https://au.indeed.com/viewjob?jk=1", None, ""):
            self.assertTrue(adsource.needs_user_ad(u), u)
        for u in ("https://careers.tasports.com.au/job/1", "https://hydro.wd3.myworkdayjobs.com/x/job/1",
                  "https://notseek.com.au.example.org/job"):
            self.assertFalse(adsource.needs_user_ad(u), u)

    def test_save_text_and_checks(self):
        res = adsource.save("27", text=AD, title="Project Officer", employer="Acme Water")
        self.assertEqual(res["status"], "saved"); self.assertTrue(res["matches_offer"])
        body = Path(res["file"]).read_text()
        self.assertIn("data, not instructions", body); self.assertIn("coordinate capital works", body)
        self.assertTrue(adsource.has_ad("27"))
        self.assertEqual(adsource.save("28", text="Project Officer\nAcme")["status"], "too_short")
        self.assertEqual(adsource.save("28; rm", text=AD)["status"], "refused")
        f = Path(self.tmp.name) / "ad.docx"; f.write_bytes(b"x")
        self.assertEqual(adsource.save("29", file=str(f))["status"], "refused")
        self.assertFalse(adsource.save("30", text=AD, title="Asset Planner", employer="Other Co")["matches_offer"])


class PrepareAsksForAd(Base):
    def _req(self, url):
        with mock.patch("hcb.prepare_request.known", return_value=True), \
             mock.patch("hcb.prepare_request.job_url", return_value=url), \
             mock.patch("hcb.prepare_request.describe", return_value=("Project Officer", "Acme Water")):
            w = lambda *a, **k: {"write_performed": True, "verified": True}
            return prepare_request.request("27", "1", writer=w)

    def test_portal_offer_waits_for_the_pdf_then_starts(self):
        first = self._req("https://email.s.seek.com.au/uni/ss/c/abc")
        self.assertEqual(first["status"], "needs_ad"); self.assertIn("Aviso 27", first["confirmation"])
        self.assertNotIn("instruction", first)                           # nothing handed to the PM
        adsource.save("27", text=AD)
        self.assertEqual(self._req("https://email.s.seek.com.au/uni/ss/c/abc")["status"], "started")

    def test_employer_page_starts_at_once_and_outage_never_blocks(self):
        self.assertEqual(self._req("https://careers.tasports.com.au/job/1")["status"], "started")

    def test_baserow_down_does_not_block(self):
        self.assertEqual(self._req("unknown")["status"], "started")


class ParseAndDigest(Base):
    def test_aviso_with_document(self):
        r = commands.parse("Aviso 27\n[The user sent a document: 'job.pdf'. It is saved at: /tmp/c/doc_1_job.pdf. Read it.]")
        self.assertEqual((r["intent"], r["ref"], r["file"]), ("ad_supplied", "27", "/tmp/c/doc_1_job.pdf"))
        self.assertTrue(commands.parse("aviso 27: " + AD)["has_text"])
        self.assertEqual(commands.parse("Aviso o-abc123")["ref"], "o-abc123")

    def test_digest_marks_portal_offers(self):
        base = {"ranking_category": "principal", "ad_text": "", "fit": None, "discovered_at": "2026-11-24T07:00:00+11:00",
                "target_match": {"group": "C", "match": "exact"}, "title": "Project Officer"}
        items = [dict(base, baserow_id=31, employer="Acme", employer_url="https://email.s.seek.com.au/x"),
                 dict(base, baserow_id=32, employer="Hydro", employer_url="https://careers.hydro.com.au/job/2")]
        self.assertTrue(daily._needs_pdf(items[0])); self.assertFalse(daily._needs_pdf(items[1]))


class RegisterPortalCards(Base):
    CARD = {"title": "Project Manager Assistant", "employer": "Example Engineering", "ranking_category": "pendiente_revision",
            "review_reason": "revisar funciones; abrir en SEEK", "url": "https://email.s.seek.com.au/uni/ss/c/x",
            "ad_text": "Project Manager Assistant\nExample Engineering\nRocherlea TAS"}

    def test_portal_card_is_kept_but_other_field_is_not(self):
        from hcb import registry
        self.assertTrue(registry.kept(dict(self.CARD), "2026-11-22"))
        other = dict(self.CARD, url="https://careers.example.com/job/1", ad_text="x" * 900)
        self.assertFalse(registry.kept(other, "2026-11-22"))                        # a read ad from another field
        self.assertFalse(registry.kept(dict(self.CARD, title="Project Manager"), "2026-11-22"))
        self.assertFalse(registry.kept(dict(self.CARD, title="Registered Nurse Assistant"), "2026-11-22"))

    def test_same_employer_and_title_is_not_registered_twice(self):
        import json
        from hcb import registry
        snap = Path(self.tmp.name) / "snap.json"
        snap.write_text(json.dumps({"opportunities": [dict(self.CARD, title="Project Controls Officer", employer="TasPorts")]}))
        live = [{"id": 29, "Company": "TasPorts", "Job Title": "Project Controls Officer", "Status": {"value": "Preparing"},
                 "Opportunity Ref": "SEEK-95841056"}]
        calls = []
        res = registry.register_snapshot(snap, "2026-11-22", live=False, live_rows=live,
                                         writer=lambda *a, **k: calls.append(a) or {})
        self.assertEqual(res["results"][0]["action"], "already_in_baserow"); self.assertEqual(calls, [])


    def test_digest_skips_offers_already_being_prepared_and_labels_cards(self):
        from datetime import datetime
        now = datetime.fromisoformat("2026-11-22T21:35:00+11:00")
        base = dict(self.CARD, discovered_at="2026-11-22T21:26:00+11:00")
        snap = {"opportunities": [dict(base, baserow_id=32, tracked_status="Discovered"),
                                  dict(base, title="Project Controls Officer", employer="TasPorts", baserow_id=29,
                                       tracked_status="Preparing")]}
        d = daily.build_digest(snap, now)
        self.assertEqual([i["baserow_id"] for i in d["items"]], [32])
        self.assertIn("falta el aviso completo", d["message"]); self.assertIn("Aviso 32", d["message"])
        self.assertNotIn("revisar funciones", d["message"])


if __name__ == "__main__":
    unittest.main()


class PastedAdWithoutPrefix(unittest.TestCase):
    """The user, 2026-11-23: after 'needs_ad' they pasted the ad text alone, without 'Aviso 32'."""
    def setUp(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        self.tmp = tempfile.TemporaryDirectory()
        self.p = mock.patch("hcb.state.project_path", side_effect=lambda k: Path(self.tmp.name))
        self.p.start()

    def tearDown(self):
        self.p.stop(); self.tmp.cleanup()

    def test_long_text_after_request_is_that_ad(self):
        from hcb import commands, state
        ad = "Project Manager Assistant\nAcme | Rocherlea, TAS\n" + "Duties include scheduling and reporting. " * 15
        self.assertEqual(commands.parse(ad)["intent"], "unknown")             # nothing was asked
        state.event("prepare_request_needs_ad", ref="32", user="1")
        res = commands.parse(ad)
        self.assertEqual((res["intent"], res["ref"], res["inferred"]), ("ad_supplied", "32", True))
        self.assertEqual(commands.parse("hola, ¿cómo va?")["intent"], "unknown")  # short chat is not an ad
        state.event("ad_saved", ref="32", origin="pasted_text", chars=900)
        self.assertEqual(commands.parse(ad)["intent"], "unknown")             # already saved
