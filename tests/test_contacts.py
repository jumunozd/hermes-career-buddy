"""P-2 early-hiring contacts: deterministic policy, trigger, validation and outreach lint."""
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from hcb import commands, contacts, daily, envelopes

TZ = ZoneInfo("Australia/Hobart")
NOW = datetime(2026, 11, 16, 6, 0, tzinfo=TZ)
ROOT = Path(__file__).resolve().parents[1]
from hcb import util  # noqa: E402
TASPORTS_AD = util.private_dir() / "state/ads/seek-95841056.txt"   # real ad, private zone (P-5)
needs_tasports = unittest.skipUnless(TASPORTS_AD.exists(), "real TasPorts ad only in the private zone")

PRIVATE_AD = """Operations Analyst - Hobart
Reporting to the Operations Manager, you will improve processes and reporting.
Applications through our careers page. For enquiries, contact Sarah Mitchell on 0412 345 678."""
NO_APPROACH_AD = """Process Engineer
Canvassing of any kind will disqualify applicants. Apply online only."""
AGENCY_AD = """Our client, a Tasmanian manufacturer, seeks a Continuous Improvement Analyst.
Call Tom Baker at Hays on 03 6230 1234 for a confidential discussion."""


def opp(**kw):
    base = {"baserow_id": 1, "employer": "Acme Foods", "title": "Operations Analyst", "fit": 70,
            "ranking_category": "principal", "entry_signal": None, "discovered_at": "2026-11-16T05:10:00+11:00",
            "posted_at": "2026-11-15T15:00:00+11:00", "ad_text": PRIVATE_AD}
    base.update(kw)
    return base


def good_contact(**kw):
    c = {"priority": "hiring_manager", "name": "Alex Chen", "title": "Operations Manager", "employer": "Acme Foods",
         "why_relevant": "The role reports to the Operations Manager.", "source_url": "https://acmefoods.com.au/team",
         "observed_at": "2026-11-16", "confidence": "confirmed", "channel": "linkedin",
         "linkedin_url": "https://au.linkedin.com/in/alex-chen-ops"}
    c.update(kw)
    return c


class Policy(unittest.TestCase):
    @needs_tasports
    def test_tasports_is_government_ad_inbox_only(self):
        ad = TASPORTS_AD.read_text(encoding="utf-8")
        p = contacts.policy(ad, "TasPorts")
        self.assertEqual(p["employer_type"], "government")
        self.assertFalse(p["people_research_allowed"])
        self.assertEqual(p["from_ad"][0]["priority"], "careers_inbox")
        self.assertEqual(p["from_ad"][0]["professional_email"], "recruitment@tasports.com.au")

    def test_no_approach_clause_blocks_people(self):  # extra test: canvassing clause
        p = contacts.policy(NO_APPROACH_AD, "Acme Foods")
        self.assertIn("Canvassing", p["no_approach_clause"])
        self.assertEqual(p["allowed_priorities"], ["careers_inbox"])
        self.assertFalse(p["people_research_allowed"])

    def test_agency_consultant_only(self):  # extra test: agency ad
        p = contacts.policy(AGENCY_AD, "Hays")
        self.assertEqual(p["employer_type"], "agency")
        self.assertEqual(p["allowed_priorities"], ["ad_named"])
        self.assertEqual(p["from_ad"][0]["name"], "Tom Baker")

    def test_private_named_contact_comes_from_ad(self):
        p = contacts.policy(PRIVATE_AD, "Acme Foods")
        self.assertEqual(p["employer_type"], "private")
        self.assertEqual(p["from_ad"][0], {"priority": "ad_named", "name": "Sarah Mitchell", "confidence": "confirmed",
                                           "source_url": "ad", "phone_from_ad": "0412 345 678"})


class Trigger(unittest.TestCase):
    def test_fresh_principal_private_runs(self):
        r = contacts.trigger([opp()], NOW)
        self.assertEqual(len(r["run"]), 1)
        self.assertEqual(r["run"][0]["contacts_needed"], 1)   # the ad already names one person
        self.assertFalse(r["contact_performed"])

    def test_skips(self):
        r = contacts.trigger([
            opp(baserow_id=2, posted_at="2026-11-13T09:00:00+11:00"),
            opp(baserow_id=3, ranking_category="exploratoria", entry_signal="Neutral"),
            opp(baserow_id=4, ad_text=NO_APPROACH_AD),
            opp(baserow_id=5, employer="TasPorts"),
            opp(baserow_id=6, ah_recommendation="DO_NOT_RECOMMEND"),
            opp(baserow_id=7, employer_contacted_before=True),   # acceptance test 7
        ], NOW)
        self.assertEqual(r["run"], [])
        self.assertEqual({s["baserow_id"] for s in r["skipped"]}, {2, 3, 4, 5, 6, 7})

    def test_strategic_entry_exploratory_runs_and_cap_of_three(self):
        ops = [opp(baserow_id=i, fit=60 + i) for i in range(4)] + \
              [opp(baserow_id=9, ranking_category="exploratoria", entry_signal="Strategic Entry", fit=90)]
        r = contacts.trigger(ops, NOW)
        self.assertEqual([o["baserow_id"] for o in r["run"]], [9, 3, 2])
        self.assertIn("cap of 3", r["skipped"][-1]["skip_reasons"][0])


class Validate(unittest.TestCase):
    def test_acceptance_1_public_hr_email_ok(self):
        res = {"contacts": [good_contact(priority="talent_acquisition", name="Kim Lee", title="Talent Partner",
                                         professional_email="careers@acmefoods.com.au",
                                         email_status="verified_public_business",
                                         email_source_url="https://acmefoods.com.au/careers")]}
        self.assertEqual(contacts.validate(res, PRIVATE_AD, "Acme Foods"), [])

    def test_acceptance_4_linkedin_only_no_email(self):
        ok = {"contacts": [good_contact(source_url="https://au.linkedin.com/in/alex-chen-ops", confidence="inferred")]}
        self.assertEqual(contacts.validate(ok, PRIVATE_AD, "Acme Foods"), [])
        bad = {"contacts": [good_contact(source_url="https://au.linkedin.com/in/alex-chen-ops", confidence="confirmed")]}
        self.assertTrue(any("cannot confirm" in p for p in contacts.validate(bad, PRIVATE_AD, "Acme Foods")))

    def test_personal_or_unverified_email_rejected(self):
        res = {"contacts": [good_contact(professional_email="alex.chen@gmail.com",
                                         email_status="verified_public_business", email_source_url="x")]}
        self.assertTrue(any("personal email" in p for p in contacts.validate(res, PRIVATE_AD, "Acme Foods")))
        guessed = {"contacts": [good_contact(professional_email="alex.chen@acmefoods.com.au", email_status="not_verified")]}
        self.assertTrue(any("verified_public_business" in p for p in contacts.validate(guessed, PRIVATE_AD, "Acme Foods")))

    def test_max_two_and_no_extra_fields(self):
        res = {"contacts": [good_contact(), good_contact(name="B"), good_contact(name="C", home_suburb="Sandy Bay")]}
        probs = contacts.validate(res, PRIVATE_AD, "Acme Foods")
        self.assertTrue(any("> max 2" in p for p in probs))
        self.assertTrue(any("not allowed" in p and "home_suburb" in p for p in probs))

    @needs_tasports
    def test_policy_enforced_on_results(self):
        probs = contacts.validate({"contacts": [good_contact(employer="TasPorts")]},
                                  TASPORTS_AD.read_text(encoding="utf-8"), "TasPorts")
        self.assertTrue(any("not allowed for government" in p for p in probs))
        probs = contacts.validate({"contacts": [good_contact()]}, NO_APPROACH_AD, "Acme Foods")
        self.assertTrue(any("no-approach" in p for p in probs))

    def test_acceptance_8_zero_contacts_is_valid(self):
        self.assertEqual(contacts.validate({"contacts": []}, PRIVATE_AD, "Acme Foods"), [])

    def test_sending_is_out_of_role(self):
        probs = contacts.validate({"contacts": [], "email_sent": True}, PRIVATE_AD, "Acme Foods")
        self.assertTrue(any("out-of-role" in p for p in probs))


class OutreachAndWiring(unittest.TestCase):
    NOTE = ("Hi Alex,\n"
            "I have applied for the Operations Analyst role through your careers page.\n"
            "At Lucky Seven I led weekly stock and sales reporting in Excel for the owner.\n"
            "Your recent move to a second production line in Cambridge caught my eye.\n"
            "Would you be open to a 10-minute call this week about the team's priorities?\n"
            "Kind regards,\nAlex Example")

    def test_lint_ok_and_failures(self):
        self.assertTrue(contacts.outreach_lint(self.NOTE)["ok"])
        long = "Hi Alex,\n" + "\n".join(["I hope this email finds you well."] * 7) + "\nRegards,\nJuan"
        r = contacts.outreach_lint(long)
        self.assertFalse(r["ok"])
        self.assertTrue(any("generic opener" in p for p in r["problems"]))

    def test_actions_and_command(self):
        envelopes.make_task("research_agent", "contact_research", ["X"], "c", "contact_research_only")
        envelopes.make_task("writer", "outreach_draft", ["X"], "c", "outreach_draft_only")
        envelopes.make_task("recruiter", "outreach_check", ["X"], "c", "outreach_draft_only")
        with self.assertRaises(ValueError):
            envelopes.make_task("job_hunter", "contact_research", ["X"], "c", "x")
        p = commands.parse("Prepara contacto 12")
        self.assertEqual((p["intent"], p["authorises"]), ("prepare_contact", "outreach_draft_only"))
        self.assertEqual(commands.parse("Contacta a Alex")["intent"], "refused")

    def test_digest_shows_contacts_and_clause(self):
        msg = daily.render_message([{
            "baserow_id": 7, "title": "Operations Analyst", "employer": "Acme Foods", "category": "principal",
            "fit": 70, "closing_date": None, "hours_since_posted": 3, "call_suggestion": None,
            "research_contacts": [good_contact(confidence="inferred")], "no_approach_clause": None}], NOW)
        self.assertIn("👤 Alex Chen, Operations Manager (fuente: acmefoods.com.au, inferido) · LinkedIn", msg)
        self.assertIn("Prepara contacto 7", msg)
        msg2 = daily.render_message([{
            "baserow_id": 8, "title": "Process Engineer", "employer": "Acme", "category": "principal", "fit": 70,
            "closing_date": None, "hours_since_posted": 3, "call_suggestion": None, "research_contacts": [],
            "no_approach_clause": "Canvassing of any kind will disqualify applicants."}], NOW)
        self.assertIn("⛔", msg2)
        self.assertNotIn("Prepara contacto", msg2)


if __name__ == "__main__":
    unittest.main()


class Duplicates(unittest.TestCase):
    def setUp(self):
        import tempfile
        from unittest import mock
        from hcb import util
        self.tmp = tempfile.TemporaryDirectory()
        cfg = dict(util.config()); cfg["paths"] = {**cfg["paths"], "state": self.tmp.name, "reports": self.tmp.name, "applications": self.tmp.name}
        self.p = mock.patch.object(util, "config", return_value=cfg)
        self.p.start()

    def tearDown(self):
        self.p.stop(); self.tmp.cleanup()

    def test_seen_log_same_job_any_url(self):
        from hcb import seen
        a = "https://au.seek.com/job/95841056?type=standard"
        b = "https://www.seek.com.au/job/95841056"
        self.assertEqual(seen.dedup_key(a), seen.dedup_key(b))
        self.assertEqual(seen.check(a, "ad text")["status"], "new")
        seen.add(a, "ad text", "baserow", "registered", "TasPorts", "Project Controls Officer", "Hobart")
        self.assertEqual(seen.check(b, "ad  TEXT")["status"], "known_unchanged")
        self.assertEqual(seen.check(b, "ad text, closing date extended")["status"], "known_changed")
        other = seen.check("https://careers.tasports.com.au/jobs/123", "x", "TasPorts", "Project Controls Officer", "Hobart")
        self.assertEqual(other["status"], "possible_duplicate")

    def test_digest_never_repeats_an_offer(self):
        snap = {"opportunities": [{"baserow_id": 41, "employer": "Acme", "title": "Operations Analyst",
                                   "ranking_category": "principal", "fit": 70,
                                   "discovered_at": "2026-11-16T05:10:00+11:00", "ad_text": ""}]}
        first = daily.build_digest(snap, NOW, already_notified=daily.notified_ids())
        self.assertEqual(len(first["items"]), 1)
        path = daily.save(first)
        daily.mark_delivered(path, "telegram", "msg-1")
        later = NOW.replace(hour=21)
        second = daily.build_digest(snap, later, already_notified=daily.notified_ids())
        self.assertEqual(second["items"], [])

    def test_failed_or_unconfirmed_delivery_keeps_the_offer(self):
        """Hermes review 2026-11-17: saving a digest must not mark offers notified before delivery."""
        snap = {"opportunities": [{"baserow_id": 42, "employer": "Acme", "title": "Operations Analyst",
                                   "ranking_category": "principal", "fit": 70,
                                   "discovered_at": "2026-11-16T05:10:00+11:00", "ad_text": ""}]}
        path = daily.save(daily.build_digest(snap, NOW, already_notified=daily.notified_ids()))
        self.assertNotIn("42", daily.notified_ids())                      # saved, not yet sent
        later = NOW.replace(hour=12)
        self.assertEqual(len(daily.build_digest(snap, later, already_notified=daily.notified_ids())["items"]), 1)
        res = daily.mark_delivered(path, "telegram", error="Telegram 502")
        self.assertEqual((res["status"], res["marked"]), ("failed", 0))
        self.assertNotIn("42", daily.notified_ids())                      # failure: comes back next run
        retry = daily.save(daily.build_digest(snap, later, already_notified=daily.notified_ids()))
        self.assertEqual(daily.mark_delivered(retry, "telegram", "msg-2")["marked"], 1)
        self.assertEqual(daily.mark_delivered(retry, "telegram", "msg-2")["marked"], 0)   # idempotent
        self.assertEqual(sum(r["baserow_id"] == 42 for r in daily.state._read("notified.jsonl")), 1)

    def test_contacts_not_researched_twice(self):
        r = contacts.trigger([opp(research_contacts=[good_contact()])], NOW)
        self.assertEqual(r["run"], [])
        self.assertIn("already researched", r["skipped"][0]["skip_reasons"][0])


class SourceCadence(unittest.TestCase):
    def test_due_by_run(self):
        from hcb import sources
        tue_first = sources.due(datetime(2026, 11, 17, 7, 30, tzinfo=TZ))
        tue_noon = sources.due(datetime(2026, 11, 17, 12, 30, tzinfo=TZ))
        mon_first = sources.due(datetime(2026, 11, 16, 7, 30, tzinfo=TZ))
        sat = sources.due(datetime(2026, 11, 21, 7, 30, tzinfo=TZ))
        ids = lambda r: {s["id"] for s in r["run"]}
        self.assertIn("EMP-NYRSTAR", ids(tue_first))
        self.assertNotIn("EMP-HYDRO", ids(tue_first))   # withdrawn in RT-15 (robots Disallow on the serving host)
        self.assertNotIn("EMP-HYDRO", ids(tue_noon))
        self.assertEqual(ids(tue_noon), {"SRC-01", "COUNCIL-GLENORCHY", "COUNCIL-DEVONPORT"})
        self.assertIn("EMP-HUON", ids(mon_first))
        self.assertNotIn("EMP-HYDRO", ids(mon_first))
        self.assertEqual(sat["run"], [])
        glen = next(s for s in tue_noon["run"] if s["id"] == "COUNCIL-GLENORCHY")
        self.assertEqual(glen["gap_s"], 20)


class RT13Fixes(unittest.TestCase):
    def test_shared_listing_page_does_not_collapse(self):
        from hcb import seen
        a = seen.dedup_key("https://www.huonaqua.com.au/careers/current-jobs/#logistics-manager")
        b = seen.dedup_key("https://www.huonaqua.com.au/careers/current-jobs/#remote-feed-operator")
        self.assertNotEqual(a, b)
        self.assertEqual(seen.dedup_key("https://x.com/jobs?id=12&utm=a"), seen.dedup_key("https://x.com/jobs?utm=b&id=12"))

    def test_single_word_catalogue_title_needs_exact(self):
        from hcb import targets
        self.assertNotEqual(targets.match_title("Senior Electrical Design Engineer")["catalogue_title"], "Graduate Engineer")
        self.assertEqual(targets.match_title("Graduate Engineer")["match"], "exact")

    def test_digest_ref_when_no_baserow_id(self):
        o = {"baserow_id": None, "opportunity_ref": "RT-13:hazell-284", "employer": "Hazell", "title": "X"}
        ref = daily.ref_of(o)
        self.assertRegex(ref, r"^o-[0-9a-f]{6}$")
        self.assertEqual(commands.parse(f"Prepara la oferta {ref}")["by"], "digest_ref")
        self.assertEqual(daily.ref_of({"baserow_id": 42}), 42)

    def test_paced_read_waits_and_refuses_disabled(self):
        import tempfile
        from unittest import mock
        from hcb import sources, util
        tmp = tempfile.TemporaryDirectory()
        cfg = dict(util.config()); cfg["paths"] = {**cfg["paths"], "state": tmp.name, "reports": tmp.name}
        with mock.patch.object(util, "config", return_value=cfg):
            slept = []
            fake = lambda u: {"ok": True, "items": [{"text": "job " * 100}]}
            now = [datetime(2026, 11, 16, 7, 30, tzinfo=TZ)]
            r1 = sources.read("SRC-01", reader=fake, now_fn=lambda: now[0], sleep_fn=slept.append)
            now[0] = now[0].replace(second=5)
            r2 = sources.read("COUNCIL-GLENORCHY", reader=fake, now_fn=lambda: now[0], sleep_fn=slept.append)
            self.assertTrue(r1["ok"] and r2["ok"])
            self.assertEqual(slept, [15.0])            # Glenorchy crawl-delay 20 s minus 5 s elapsed
            self.assertFalse(sources.read("SRC-03")["ok"])   # SEEK is disabled
            self.assertFalse(sources.read("SRC-01", url="https://evil.example/x", reader=fake)["ok"])
        off = dict(cfg); off["features"] = {**cfg["features"], "web_discovery": False}
        called = []
        with mock.patch.object(util, "config", return_value=off):
            r = sources.read("SRC-01", reader=lambda u: called.append(u) or {"ok": True, "items": []})
        self.assertFalse(r["ok"]); self.assertIn("web_discovery", r["error"]); self.assertEqual(called, [])
        tmp.cleanup()


class RT14Fixes(Duplicates):
    def test_seen_status_from_card_identity_not_text(self):
        from hcb import seen
        u = "https://careers.gotosage.com/jobs/7882977-service-electrician"
        seen.add(u, "FULL AD TEXT " * 50, "excluded", "C1", "SAGE Automation", "Service Electrician", "Brisbane")
        r = seen.check(u, "card text only", "SAGE Automation", "Service Electrician", "Brisbane", "2026-12-01")
        self.assertEqual(r["status"], "known_unchanged")             # legacy entry, no closing recorded
        seen.add(u, "card", "excluded", "C1", "SAGE Automation", "Service Electrician", "Brisbane", closing="2026-12-01")
        self.assertEqual(seen.check(u, "x", "SAGE Automation", "Service Electrician", "Brisbane", "2026-12-01")["status"],
                         "known_unchanged")
        self.assertEqual(seen.check(u, "x", "SAGE Automation", "Service Electrician", "Brisbane", "2026-12-15")["status"],
                         "known_changed")

    def test_same_job_same_site_new_url_format_is_known(self):
        from hcb import seen
        seen.add("https://www.huonaqua.com.au/careers/current-jobs/", "t", "excluded", "C1", "Huon Aquaculture",
                 "Farm Attendant", "Dover")
        r = seen.check("https://www.huonaqua.com.au/careers/current-jobs/#493865", "t2", "Huon Aquaculture",
                       "Farm Attendant", "Dover")
        self.assertEqual(r["status"], "known_unchanged")
        r = seen.check("https://www.seek.com.au/job/1", "t2", "Huon Aquaculture", "Farm Attendant", "Dover")
        self.assertEqual(r["status"], "possible_duplicate")

    def test_card_triage(self):
        from hcb import targets
        self.assertFalse(targets.triage("Registered Nurse (502371L2)", "North West")["read_detail"])
        self.assertFalse(targets.triage("Automation Technician", "North Sydney")["read_detail"])
        self.assertTrue(targets.triage("Policy and Project Officer (708791)", "South")["read_detail"])
        self.assertTrue(targets.triage("Government Business Analyst", "South")["read_detail"])   # unclear: read
        self.assertEqual(targets.zone_status("South")["status"], "region_only")
        self.assertEqual(targets.zone_status("Hobart, TAS")["status"], "in_zone")
        self.assertEqual(targets.zone_status("Huonville")["status"], "out_of_zone")

    def test_region_only_goes_to_review_not_out(self):
        from hcb import rules
        o = {"in_zone": True, "location_status": "region_only",
             "target_match": {"group": "C", "match": "contained", "category_hint": "principal_candidate"}}
        r = rules.classify(o)
        self.assertEqual((r["rule"], r["ranking_category"]), ("A2-LOC", "pendiente_revision"))
        item = daily.build_digest({"opportunities": [{**o, "employer": "NRE Tas", "title": "Policy and Project Officer",
                                                      "ranking_category": "pendiente_revision",
                                                      "discovered_at": "2026-11-16T07:00:00+11:00"}]}, NOW)["items"][0]
        self.assertIn("confirmar localidad", daily.render_message([item], NOW))

    def test_exact_title_other_field_needs_review(self):
        from hcb import targets
        ad = ("Technical Officer, pathology services\nReceive and prepare specimens in the laboratory\n"
              "Support clinical staff and patient testing\nMaintain quality systems")
        self.assertEqual(targets.assess("Technical Officer", ad)["category_hint"], "needs_review")
        hospital_ba = "Business Process Analyst\nImprove processes across clinical services\nBuild Power BI dashboards"
        self.assertNotEqual(targets.assess("Business Process Analyst", hospital_ba)["category_hint"], "needs_review")
