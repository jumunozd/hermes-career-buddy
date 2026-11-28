"""P-15 search discovery v2 (approved 2026-11-28, AP-2f90ef34afdfdbc450403293). Replays the Rio Tinto / Chandler
Macleod case: an ad the user found with ChatGPT that Hermes missed and would have registered twice."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from hcb import discovery, repair, seen

NOW = datetime(2026, 11, 28, 12, 30, tzinfo=timezone.utc)
UUID = "00d57e33-7c2c-4001-8c4c-147cd470e22a"
MOVE = f"https://movetomore.com.au/job/{UUID}/"
VIEW = f"https://www.viewjobs.com.au/listing/{UUID}"
TEXT = ("Business Analyst Specialist | Regional Jobs Business Analyst Specialist Chandler Macleod Bell Bay, Australia "
        "(On-site) Full-time Date posted: November 27, 2026 Closes: Dec 27, 2026 About the role Rio Tinto ...")


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"HCB_PRIVATE_DIR": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class Dedup(Tmp):
    def test_location_spelling_is_one_job(self):
        seen.add("", "x", "baserow", "user_selected", "Chandler Macleod", "Business Analyst Specialist",
                 "Bell Bay Tasmania")
        for loc in ("Bell Bay", "Bell Bay, TAS", "Bell Bay, Australia (On-site)", "Bell Bay TAS 7253"):
            self.assertNotEqual(seen.check(MOVE, "y", "Chandler Macleod", "Business Analyst Specialist", loc)["status"],
                                "new", loc)

    def test_shared_ad_id_across_aggregators(self):
        self.assertEqual(seen.dedup_key(MOVE), f"ad:{UUID}")
        seen.add(MOVE, "x", "baserow", "found", "Chandler Macleod", "Business Analyst Specialist", "Bell Bay")
        self.assertEqual(seen.check(VIEW, "other text", "", "Business Analyst Specialist — Chandler Macleod", "")["status"],
                         "known_unchanged")

    def test_other_place_is_still_new(self):
        seen.add("", "x", "baserow", "r", "Chandler Macleod", "Business Analyst Specialist", "Bell Bay")
        self.assertEqual(seen.check("https://example.com/a", "y", "Chandler Macleod", "Business Analyst Specialist",
                                    "Hobart")["status"], "new")


class Aggregators(unittest.TestCase):
    def test_new_patterns_are_hints_never_opened(self):
        for u in (VIEW, MOVE, "https://www.resourcejobs.au/jobs/business-analyst-specialist-3a0583d8a9fb4567b392106c1958329a",
                  "https://www.jobstralia.com/detail/8/0ccd2a9afc1b8717c951c0b46ad91217",
                  "https://au.jooble.org/jdp/7318084103472883304",
                  "https://www.zammejobs.com/jobs/c70fd500-0f8c-4cc5-8c46-de5219c8b996",
                  "https://www.chandlermacleod.com/job-details/expression-of-interest-1653768"):
            k = discovery.classify_url(u)
            self.assertIsNotNone(k, u)
            self.assertFalse(k[1], u)

    def test_portal_job_pages_never_readable(self):
        self.assertFalse(discovery.classify_url("https://www.seek.com.au/job/81234567")[1])


class Titles(unittest.TestCase):
    def test_titles_and_companies(self):
        self.assertEqual(discovery.clean_title("JLE Group hiring Project Engineer in Launceston, Tasmania, Australia | LinkedIn"),
                         "Project Engineer")
        self.assertEqual(discovery._company_from("JLE Group hiring Project Engineer in Launceston | LinkedIn"), "JLE Group")
        a = "Expression of Interest - Opportunities with Rio Tinto job in Mining Resources & Energy in Bell Bay"
        b = "Expression of Interest - Opportunities with Rio Tinto at Chandler Macleod — Bell Bay, TAS | ZammeJobs"
        self.assertEqual(discovery.clean_title(a), discovery.clean_title(b))
        self.assertEqual(discovery._company_from(b), "Chandler Macleod")
        self.assertEqual(discovery._company_from("Process Operator — Euro"), "")
        self.assertEqual(discovery._company_from("Business Analyst Specialist — Chandler Macleod | ViewJobs"), "Chandler Macleod")


class Freshness(unittest.TestCase):
    def test_dates_from_text(self):
        self.assertEqual(discovery.card_date({"text": TEXT}, NOW), "2026-11-27")
        self.assertEqual(discovery.card_date({"date_shown": "Listed nine hours ago"}, NOW), "2026-11-28")
        self.assertEqual(discovery.card_date({"date_shown": "Posted 7h ago"}, NOW), "2026-11-28")
        self.assertEqual(discovery.card_date({"date_shown": "Listed 2 weeks ago"}, NOW), "2026-11-14")
        self.assertEqual(discovery.card_date({"date_shown": "13-Nov-2026"}, NOW), "2026-11-13")
        self.assertEqual(discovery.card_date({"published_at": "2026-11-27T00:00:00.000Z"}, NOW), "2026-11-27")
        self.assertIsNone(discovery.card_date({"text": "no date here"}, NOW))

    def test_old_is_dropped(self):
        self.assertTrue(discovery._too_old("2026-09-01", NOW))
        self.assertFalse(discovery._too_old(None, NOW))


class AgencyQueries(Tmp):
    def test_agency_query_for_rio_tinto(self):
        qs = {s["id"]: discovery.query_for(s) for s in discovery.agency_sources()}
        self.assertTrue(any("Chandler Macleod" in q and "Rio Tinto" in q for q in qs.values()), qs)

    def test_replay_finds_the_ad_once(self):
        def search(q, limit):
            return {"ok": True, "items": [{"title": "Business Analyst Specialist | Regional Jobs", "url": MOVE,
                                           "published_at": "2026-11-27T00:00:00.000Z", "text": TEXT},
                                          {"title": "Business Analyst Specialist — Chandler Macleod | ViewJobs",
                                           "url": VIEW, "published_at": None, "text": TEXT}]}
        with mock.patch.object(discovery, "due_sources", lambda: [s for s in discovery.agency_sources()]):
            out = discovery.run(NOW, search=search, max_queries=1)
        cards = [c for c in out["shortlist"] if "Business Analyst Specialist" in c["title"]]
        self.assertEqual(len(cards), 1, out["shortlist"])
        self.assertEqual(cards[0]["company"], "Chandler Macleod")
        self.assertEqual(cards[0]["location"], "Bell Bay")
        self.assertEqual(cards[0]["date"], "2026-11-27")


class NativeIngest(Tmp):
    RESULTS = {"searches": [{"query": "Business Analyst Specialist Bell Bay", "results": [
        {"title": "Business Analyst Jobs in Tasmania TAS - Nov 2026 | SEEK",
         "url": "https://au.seek.com/business-analyst-jobs/in-Tasmania-TAS", "date_shown": "Listed nine hours ago",
         "snippet": "We are seeking an experienced Business Analyst Specialist to join a safety-focused team at Bell Bay Smelter.",
         "role_title": "Business Analyst Specialist", "place": "Bell Bay"},
        {"title": "Business Analyst Specialist at Chandler Macleod",
         "url": "https://www.resourcejobs.au/jobs/business-analyst-specialist-3a0583d8a9fb4567b392106c1958329a",
         "date_shown": None, "snippet": "Through Rio Tinto's partnership with Chandler Macleod, we are seeking an "
                                       "experienced Business Analyst Specialist to join a safety-focused team at Bell Bay Smelter."},
        {"title": "Made-up role", "url": "https://au.seek.com/x-jobs/in-Tasmania-TAS", "date_shown": None,
         "snippet": "Nothing about it here.", "role_title": "Chief Wizard", "place": "Hobart"},
        {"title": "CPQ Analyst - Troy, OH 45374 - Indeed.com", "url": "https://www.indeed.com/viewjob?jk=b21ffedf6d5cf75c",
         "date_shown": None, "snippet": "continuous improvement of Hobart Service's processes"}]}]}

    def test_ingest_makes_one_card_per_job_and_rejects_invented_titles(self):
        out = discovery.ingest(self.RESULTS, NOW)
        titles = [c["title"] for c in out["shortlist"]]
        self.assertEqual(titles.count("Business Analyst Specialist"), 1, out["shortlist"])
        self.assertNotIn("Chief Wizard", titles)
        self.assertTrue(all(c["channel"] == "native_search" and not c["read_detail_allowed"] for c in out["shortlist"]))
        self.assertGreaterEqual(out["stats"]["unverified_titles"], 1)

    def test_ingest_skips_what_seen_already_has(self):
        seen.add("", "x", "baserow", "user_selected", "Chandler Macleod", "Business Analyst Specialist",
                 "Bell Bay Tasmania")
        out = discovery.ingest(self.RESULTS, NOW)
        self.assertFalse([c for c in out["shortlist"] if c["title"] == "Business Analyst Specialist"], out["shortlist"])

    def test_native_queries_rotate_and_stop_after_the_trial(self):
        self.assertEqual(len(discovery.native_queries(NOW)["queries"]), 2)
        late = datetime(2027, 1, 30, tzinfo=timezone.utc)
        self.assertEqual(discovery.native_queries(late)["queries"], [])


class PortalGuard(unittest.TestCase):
    def blocked(self, tool, **args):
        return repair.guard({"tool_name": tool, "tool_input": args}) is not None

    def test_portal_pages_are_never_read(self):
        self.assertTrue(self.blocked("web_extract", urls=["https://www.seek.com.au/job/81234567"]))
        self.assertTrue(self.blocked("web_extract", urls=["https://au.linkedin.com/jobs/view/project-engineer-123"]))
        self.assertTrue(self.blocked("web_extract", urls=["https://au.indeed.com/viewjob?jk=b21ffedf6d5cf75c"]))
        self.assertTrue(self.blocked("web_extract", urls=["https://au.jora.com/job/Business-Analyst-abc"]))
        self.assertTrue(self.blocked("browser_exec", url="https://www.seek.com.au/job/81234567"))
        self.assertTrue(self.blocked("terminal", command="curl -s https://www.seek.com.au/job/81234567"))

    def test_other_pages_and_search_are_free(self):
        self.assertFalse(self.blocked("web_extract", urls=[VIEW]))
        self.assertFalse(self.blocked("web_extract", urls=["https://www.resourcejobs.au/jobs/x-1"]))
        self.assertFalse(self.blocked("web_search", query="Business Analyst site:seek.com.au"))


if __name__ == "__main__":
    unittest.main()
