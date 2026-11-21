"""Daily new-opportunity digest and contact extraction (D-USR-01)."""
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from hcb import daily

NOW = datetime(2026, 11, 14, 8, 0, tzinfo=ZoneInfo("Australia/Hobart"))


class Contacts(unittest.TestCase):
    def test_australian_formats(self):
        text = ("For enquiries contact Sarah Mitchell on 0412 345 678 or (03) 6234 5678. "
                "General line 1300 123 456. Email jobs@example.com.au")
        c = daily.extract_contacts(text)
        self.assertEqual([p["normalised"] for p in c["phones"]], ["0412345678", "0362345678", "1300123456"])
        self.assertIn("Sarah Mitchell", c["contact_names"])
        self.assertEqual(c["emails"], ["jobs@example.com.au"])

    def test_plus61_and_no_false_positives(self):
        c = daily.extract_contacts("Call +61 3 6234 5678. Salary $85,000 - $95,000. Ref 2026123456789.")
        self.assertEqual([p["normalised"] for p in c["phones"]], ["0362345678"])

    def test_masked_number_reported_not_guessed(self):
        c = daily.extract_contacts("Contact Ning Huang on 03 62xx xxxx")
        self.assertEqual(c["phones"], [])
        self.assertTrue(c["masked_phone"])

    def test_synthetic_ad_has_no_phone(self):
        ad = Path(__file__).parent / "fixtures" / "synthetic-ad-ci-coordinator.txt"
        self.assertEqual(daily.extract_contacts(ad.read_text())["phones"], [])


class Digest(unittest.TestCase):
    def snap(self):
        return {"opportunities": [
            {"baserow_id": 1, "employer": "A", "title": "Planner", "fit": 72, "ranking_category": "principal",
             "discovered_at": "2026-11-14T06:30:00+11:00", "posted_at": "2026-11-13T15:00:00+11:00",
             "closing_date": "2026-11-30", "ad_text": "Contact Tom Price on 0400 111 222"},
            {"baserow_id": 2, "employer": "B", "title": "Coordinator", "fit": None, "ranking_category": "pendiente_revision",
             "discovered_at": "2026-11-14T07:00:00+11:00", "posted_at": None, "ad_text": ""},
            {"baserow_id": 3, "employer": "C", "title": "Old", "fit": 80, "ranking_category": "principal",
             "discovered_at": "2026-11-10T07:00:00+11:00"},
            {"baserow_id": 4, "employer": "D", "title": "Below", "fit": 40, "ranking_category": None,
             "discovered_at": "2026-11-14T07:00:00+11:00"},
            {"baserow_id": 5, "employer": "E", "title": "Closed", "fit": 75, "ranking_category": "principal",
             "estado": "Cerrada", "discovered_at": "2026-11-14T07:00:00+11:00"}]}

    def test_only_new_eligible_in_window(self):
        d = daily.build_digest(self.snap(), NOW)
        self.assertEqual([i["baserow_id"] for i in d["items"]], [1, 2])

    def test_call_suggestion_and_24h_flag(self):
        item = daily.build_digest(self.snap(), NOW)["items"][0]
        self.assertTrue(item["within_24h_window"])
        self.assertEqual(item["hours_since_posted"], 17.0)
        self.assertIn("0400 111 222", item["call_suggestion"])
        self.assertIn("Tom Price", item["call_suggestion"])

    def test_digest_never_contacts_or_authorises(self):
        d = daily.build_digest(self.snap(), NOW)
        self.assertFalse(d["contact_performed"])
        self.assertEqual(d["authorises"], "nothing")
        self.assertIn("no llama ni postula", d["message"])
        self.assertIn("Prepara la oferta 1", d["message"])

    def test_empty_day(self):
        self.assertIn("no hay ofertas nuevas", daily.build_digest({"opportunities": []}, NOW)["message"])


if __name__ == "__main__":
    unittest.main()


class OneOrdering(unittest.TestCase):
    """Hermes review 2026-11-17: digest order == rules.alignment_key (the Top 5 order), within a category."""
    def test_digest_follows_alignment_key(self):
        from hcb import rules
        base = {"employer": "Acme", "ranking_category": "principal", "discovered_at": "2026-11-14T07:00:00+11:00",
                "ad_text": "", "fit": None}
        opps = [
            {**base, "baserow_id": "contained", "title": "Supply Operations Analyst",
             "target_match": {"group": "A", "match": "contained"}, "closing_date": "2026-11-20", "fit": 90},
            {**base, "baserow_id": "exact", "title": "Operations Analyst",
             "target_match": {"group": "A", "match": "exact"}, "closing_date": "2026-12-01", "fit": 10},
            {**base, "baserow_id": "groupB", "title": "Project Officer",
             "target_match": {"group": "B", "match": "exact"}, "entry_signal": "Strategic Entry"},
            {**base, "baserow_id": "explor", "title": "Analyst", "ranking_category": "exploratoria",
             "target_match": {"group": "A", "match": "exact"}},
        ]
        got = [i["baserow_id"] for i in daily.build_digest({"opportunities": opps}, NOW)["items"]]
        want = [o["baserow_id"] for o in sorted(opps[:3], key=rules.alignment_key)] + ["explor"]
        self.assertEqual(got, want)
        self.assertEqual(got[:2], ["exact", "contained"])


class HermesReview2(unittest.TestCase):
    """Second Hermes review, 2026-11-17."""
    def test_no_call_hint_when_the_ad_forbids_contact(self):
        o = {"baserow_id": "o-aaaaaa", "employer": "Acme", "title": "Operations Analyst",
             "ranking_category": "principal", "discovered_at": "2026-11-14T07:00:00+11:00", "fit": None,
             "ad_text": "For enquiries contact Sarah Mitchell on 0412 345 678.",
             "no_approach_clause": "Canvassing will disqualify",
             "research_contacts": [{"name": "Pat Lee", "title": "Ops Manager", "source_url": "https://x.example/a"}]}
        d = daily.build_digest({"opportunities": [o]}, NOW)
        item = d["items"][0]
        self.assertIsNone(item["call_suggestion"]); self.assertEqual(item["research_contacts"], [])
        self.assertNotIn("Llamar hoy", d["message"]); self.assertNotIn("Prepara contacto", d["message"])
        self.assertIn("no contactar", d["message"])

    def test_retries_never_overwrite_a_saved_digest(self):
        import tempfile
        from unittest import mock
        from hcb import util
        with tempfile.TemporaryDirectory() as tmp:
            cfg = dict(util.config()); cfg["paths"] = {**cfg["paths"], "reports": tmp, "state": tmp}
            with mock.patch.object(util, "config", return_value=cfg), \
                 mock.patch("hcb.daily.project_path", side_effect=lambda k: Path(tmp)):
                d = daily.build_digest({"opportunities": []}, NOW)
                paths = {daily.save(dict(d)) for _ in range(4)}
        self.assertEqual(len(paths), 4)


class Send(unittest.TestCase):
    """bin/hcb daily-send: hermes send result -> delivered / failed (exit code is 0 even on failure)."""
    def _run(self, stdout, code=0):
        import tempfile
        from types import SimpleNamespace
        from unittest import mock
        from hcb import util
        with tempfile.TemporaryDirectory() as tmp:
            cfg = dict(util.config()); cfg["features"] = {**cfg["features"], "telegram_delivery": True}
            cfg["paths"] = {**cfg["paths"], "state": tmp}
            snap = {"opportunities": [{"baserow_id": "o-abc123", "employer": "Acme", "title": "Operations Analyst",
                                       "ranking_category": "principal", "fit": None, "ad_text": "",
                                       "discovered_at": "2026-11-14T07:00:00+11:00"}]}
            with mock.patch.object(util, "config", return_value=cfg), \
                 mock.patch("hcb.daily.config", return_value=cfg), \
                 mock.patch("hcb.daily.project_path", side_effect=lambda k: Path(tmp)), \
                 mock.patch("hcb.state.project_path", side_effect=lambda k: Path(tmp)):
                path = daily.save(daily.build_digest(snap, NOW))
                calls = []
                res = daily.send(path, runner=lambda c: calls.append(c) or SimpleNamespace(returncode=code, stdout=stdout, stderr=""))
                return res, calls, daily.notified_ids()

    def test_success_marks_notified(self):
        res, calls, notified = self._run('warning\n{"chat_id": "1", "message_id": "53", "mirrored": true}')
        self.assertEqual(res["status"], "delivered"); self.assertIn("o-abc123", notified)
        self.assertEqual(calls[0][:4], ["hermes", "-p", "career-buddy", "send"])

    def test_error_json_with_exit_zero_is_a_failure(self):
        res, _, notified = self._run('{"error": "Telegram send failed: httpx.ConnectError: "}')
        self.assertEqual(res["status"], "failed"); self.assertNotIn("o-abc123", notified)

    def test_off_switch_sends_nothing(self):
        from unittest import mock
        from hcb import util
        cfg = dict(util.config()); cfg["features"] = {**cfg["features"], "telegram_delivery": False}
        import tempfile, json as _j
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "d.json"; f.write_text(_j.dumps({"digest_id": "D-x", "items": [{"baserow_id": 1}], "message": "m"}))
            with mock.patch("hcb.daily.config", return_value=cfg):
                self.assertEqual(daily.send(f, runner=lambda c: 1 / 0)["status"], "not_sent")


class FallbackOnce(unittest.TestCase):
    """The user, 2026-11-17: only on the first unattended day, an empty run sends the best 3 already found."""
    def _env(self, tmp, fb_date="2026-11-18"):
        import json as _j
        from unittest import mock
        from hcb import util
        cfg = dict(util.config())
        cfg["daily_alert"] = {**cfg["daily_alert"], "fallback_once": {"date": fb_date, "top_n": 2,
                              "candidates_file": "cands.json", "exclude_titles": ["Bad Match"]}}
        base = {"employer": "Acme", "ranking_category": "pendiente_revision", "ad_text": "", "fit": None,
                "discovered_at": "2026-11-16T07:00:00+11:00"}
        opps = [{**base, "baserow_id": "o-aaaaa1", "title": "Bad Match", "target_match": {"group": "A", "match": "exact"}},
                {**base, "baserow_id": "o-aaaaa2", "title": "Project Officer", "target_match": {"group": "C", "match": "contained"},
                 "closing_date": "2026-11-25"},
                {**base, "baserow_id": "o-aaaaa3", "title": "Operations Coordinator", "target_match": {"group": "B", "match": "exact"},
                 "closing_date": "2026-11-30"},
                {**base, "baserow_id": "o-aaaaa4", "title": "Closed Already", "target_match": {"group": "A", "match": "exact"},
                 "closing_date": "2026-11-10"},
                {**base, "baserow_id": "o-aaaaa5", "title": "No Group"}]
        (Path(tmp) / "state").mkdir(); (Path(tmp) / "reports" / "daily").mkdir(parents=True)
        (Path(tmp) / "cands.json").write_text(_j.dumps({"opportunities": opps}))
        return [mock.patch.object(util, "config", return_value=cfg), mock.patch("hcb.daily.config", return_value=cfg),
                mock.patch("hcb.daily.project_path", side_effect=lambda k: Path(tmp) / k),
                mock.patch("hcb.state.project_path", side_effect=lambda k: Path(tmp) / k)]

    def _with(self, fn, fb_date="2026-11-18"):
        import tempfile, contextlib
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as st:
            for p in self._env(tmp, fb_date):
                st.enter_context(p)
            return fn()

    def test_empty_first_day_sends_best_already_found(self):
        day = datetime(2026, 11, 18, 7, 30, tzinfo=ZoneInfo("Australia/Hobart"))
        d = self._with(lambda: daily.build_digest({"opportunities": []}, day, already_notified=daily.notified_ids()))
        # re-matched against today's catalogue: both are group C exact, so the sooner closing date comes first
        self.assertEqual([i["title"] for i in d["items"]], ["Project Officer", "Operations Coordinator"])
        self.assertIn("no hay ofertas nuevas", d["message"]); self.assertEqual(d["fallback_once"]["count"], 2)

    def test_nothing_good_sends_one_status_line_once(self):
        import json as _j
        day = datetime(2026, 11, 18, 7, 30, tzinfo=ZoneInfo("Australia/Hobart"))
        from types import SimpleNamespace
        def flow():
            import hcb.daily as dd
            # empty candidate pool: overwrite the candidates file with nothing usable
            src = dd.project_path("state").parent / "cands.json"
            src.write_text(_j.dumps({"opportunities": [{"baserow_id": "o-lib", "title": "Library Officer", "employer": "X",
                                                        "ranking_category": "pendiente_revision",
                                                        "target_match": {"group": "C", "match": "contained"}}]}))
            d = dd.build_digest({"opportunities": []}, day, already_notified=dd.notified_ids())
            path = dd.save(d)
            sent = dd.send(path, runner=lambda c: SimpleNamespace(returncode=0, stdout='{"message_id": "9"}', stderr=""))
            later = dd.build_digest({"opportunities": []}, day.replace(hour=12), already_notified=dd.notified_ids())
            return d, sent, later
        import tempfile, contextlib
        from hcb import util
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as st:
            for p in self._env(tmp):
                st.enter_context(p)
            cfg = util.config(); cfg["features"] = {**cfg["features"], "telegram_delivery": True}
            d, sent, later = flow()
        self.assertEqual(d["items"], []); self.assertIn("primera corrida automática OK", d["message"])
        self.assertEqual(sent["status"], "delivered")
        self.assertIsNone(later.get("fallback_once")); self.assertEqual(later["items"], [])

    def test_other_days_stay_silent(self):
        day = datetime(2026, 11, 19, 7, 30, tzinfo=ZoneInfo("Australia/Hobart"))
        d = self._with(lambda: daily.build_digest({"opportunities": []}, day))
        self.assertEqual(d["items"], [])

    def test_not_after_a_delivered_digest_that_day(self):
        day = datetime(2026, 11, 18, 12, 30, tzinfo=ZoneInfo("Australia/Hobart"))
        def run():
            first = daily.build_digest({"opportunities": []}, day.replace(hour=7))
            path = daily.save(first)
            daily.mark_delivered(path, "telegram", "m1")
            return daily.build_digest({"opportunities": []}, day, already_notified=daily.notified_ids())
        self.assertEqual(self._with(run)["items"], [])

    def test_legacy_unsent_rows_do_not_count_as_notified(self):
        def run():
            daily.state._append("notified.jsonl", {"baserow_id": "o-legacy", "digest_id": "D-old"})
            daily.state._append("notified.jsonl", {"baserow_id": "o-sent", "digest_id": "D-new", "channel": "telegram"})
            return daily.notified_ids()
        self.assertEqual(self._with(run), {"o-sent"})



class ReportSend(unittest.TestCase):
    def test_report_pdf_goes_as_media_and_is_recorded_once(self):
        import json as _j, tempfile
        from types import SimpleNamespace
        from unittest import mock
        from hcb import report, util
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "R-X"; d.mkdir()
            (d / "report.pdf").write_bytes(b"%PDF")
            (d / "report.json").write_text(_j.dumps({"report_id": "R-X", "top5": [1], "exploratory": [], "followups_recommended": [],
                                                    "within_limit": True, "page_count": 2,
                                                    "files": {"pdf": str(d / "report.pdf")}, "delivery": None}))
            cfg = dict(util.config()); cfg["features"] = {**cfg["features"], "telegram_delivery": True}
            sent = []
            run = lambda c: sent.append(Path(c[-1]).read_text()) or SimpleNamespace(returncode=0, stdout='{"message_id": "77"}', stderr="")
            with mock.patch("hcb.report.config", return_value=cfg), mock.patch("hcb.daily.config", return_value=cfg), \
                 mock.patch("hcb.report.project_path", side_effect=lambda k: Path(tmp)), \
                 mock.patch("hcb.state.project_path", side_effect=lambda k: Path(tmp)):
                first = report.send("R-X", runner=run)
                again = report.send("R-X", runner=run)
        self.assertEqual(first["status"], "delivered"); self.assertTrue(again.get("already"))
        self.assertEqual(len(sent), 1); self.assertIn("MEDIA:", sent[0])


class PrepareDocsP10(unittest.TestCase):
    def test_top3_keyboard_uses_row_ids_and_other_offers_follow(self):
        from unittest import mock
        from hcb import util
        cfg = dict(util.config()); cfg["daily_alert"] = {**cfg["daily_alert"], "layout": "top3", "fallback_once": None}
        base = {"employer": "Acme", "ranking_category": "principal", "ad_text": "", "fit": None,
                "discovered_at": "2026-11-14T07:00:00+11:00"}
        opps = [{**base, "baserow_id": 30 + n, "title": t, "target_match": {"group": g, "match": "exact"}}
                for n, (t, g) in enumerate([("Project Officer", "C"), ("Operations Analyst", "A"), ("Planning Officer", "D"),
                                            ("Process Engineer", "B"), ("Remote Feed Operator", "E")])]
        opps[-1]["ranking_category"] = "exploratoria"
        with mock.patch("hcb.daily.config", return_value=cfg):
            d = daily.build_digest({"opportunities": opps}, NOW)
        self.assertEqual([r[0]["callback_data"] for r in d["keyboard"]], ["hcb:prep:31", "hcb:prep:33", "hcb:prep:30"])
        self.assertIn("TOP 3", d["message"]); self.assertIn("OTRAS OFERTAS", d["message"]); self.assertIn("EXPLORATORIAS", d["message"])

    def test_prepare_request_is_idempotent(self):
        import tempfile
        from unittest import mock
        from hcb import prepare_request
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("hcb.state.project_path", side_effect=lambda k: Path(tmp)), \
                 mock.patch("hcb.prepare_request.known", side_effect=lambda r: r == "27"):
                calls = []
                w = lambda *a, **k: calls.append(a) or {"write_performed": True, "verified": True}
                first = prepare_request.request("27", "1", writer=w)
                again = prepare_request.request("27", "1", writer=w)
                bad = prepare_request.request("27; rm -rf /", "1", writer=w)
        self.assertEqual((first["status"], first["instruction"]), ("started", "Prepara la oferta 27"))
        self.assertEqual(again["status"], "already_requested"); self.assertEqual(len(calls), 1)
        self.assertEqual(bad["status"], "refused")

    def test_unknown_offer_is_refused(self):
        import json, tempfile
        from hcb import prepare_request
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "D-2026-11-20.json").write_text(json.dumps({"delivery": {"status": "delivered"},
                                                                   "items": [{"baserow_id": "o-7502d9"}]}))
            self.assertTrue(prepare_request.known("o-7502d9", digest_dir=tmp))
            self.assertFalse(prepare_request.known("o-abc123", digest_dir=tmp))
        self.assertTrue(prepare_request.known("27", rows=[{"id": 27}]))
        self.assertFalse(prepare_request.known("99", rows=[{"id": 27}]))

