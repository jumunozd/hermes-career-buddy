"""Target catalogue matcher (config/job-targets.yaml)."""
import unittest
from pathlib import Path

from hcb import targets

AD = Path(__file__).parent / "fixtures" / "synthetic-ad-ci-coordinator.txt"


class Targets(unittest.TestCase):
    def test_exact_and_seniority_insensitive(self):
        self.assertEqual(targets.match_title("Continuous Improvement Coordinator")["group"], "A")
        m = targets.match_title("Senior Maintenance Planner")
        self.assertEqual((m["group"], m["match"]), ("C", "exact"))
        self.assertEqual(targets.match_title("Graduate Industrial Engineer")["group"], "B")

    def test_contained_title_and_parentheses(self):
        m = targets.match_title("Business Development (BD) Support Officer")
        self.assertEqual((m["group"], m["catalogue_title"], m["match"]), ("D", "Business Support Officer", "contained"))

    def test_group_a_preferred_over_lower_groups(self):
        self.assertEqual(targets.match_title("Asset Planning Officer")["group"], "A")

    def test_unknown_title(self):
        self.assertEqual(targets.match_title("Receptionist")["match"], "none")

    def test_whole_word_signals(self):
        s = targets.duty_signals("Excellent written communication.\nHigh-quality work.")
        self.assertNotIn("analysis", s["bridge_categories"])
        self.assertNotIn("operations_technical", s["bridge_categories"])

    def test_group_e_always_exploratory(self):
        self.assertEqual(targets.assess("Production Operator", AD.read_text())["category_hint"], "exploratoria")

    def test_queries_top12_first_and_e_selective(self):
        q = targets.queries()
        self.assertEqual(q[0], "Continuous Improvement Officer")
        self.assertNotIn("Production Operator", q)
        self.assertIn("Production Operator", targets.queries(include_selective=True))


if __name__ == "__main__":
    unittest.main()


class SeniorExcluded(unittest.TestCase):
    """The user, 2026-11-17: Senior roles are out (the title already asks for experience)."""
    def test_triage_logs_senior_from_the_card(self):
        from hcb import targets
        t = targets.triage("Senior Project Officer", "Hobart")
        self.assertFalse(t["read_detail"]); self.assertEqual(t["seen_destination_if_not_read"], "seen_log:seniority_excluded")
        self.assertTrue(targets.triage("Project Officer", "Hobart")["read_detail"])
        self.assertEqual(targets.excluded_by_title("Seniors Program Coordinator"), [])   # whole word only

    def test_digest_never_announces_senior(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from hcb import daily
        now = datetime(2026, 11, 14, 8, 0, tzinfo=ZoneInfo("Australia/Hobart"))
        base = {"employer": "Acme", "ranking_category": "principal", "ad_text": "", "fit": None,
                "discovered_at": "2026-11-14T07:00:00+11:00"}
        d = daily.build_digest({"opportunities": [{**base, "baserow_id": "o-s1", "title": "Senior Policy Officer"},
                                                  {**base, "baserow_id": "o-s2", "title": "Policy Officer"}]}, now)
        self.assertEqual([i["title"] for i in d["items"]], ["Policy Officer"])


class SeniorityWordsExcluded(unittest.TestCase):
    def test_lead_principal_manager_excluded(self):
        from hcb import targets
        for t in ("Team Lead Operations", "Principal Engineer", "Operations Manager", "Project Manager"):
            self.assertFalse(targets.triage(t, "Hobart")["read_detail"], t)
        for t in ("Operations Coordinator", "Leading Hand", "Management Accountant"):
            self.assertEqual(targets.excluded_by_title(t), [], t)


class UserTitleChoices(unittest.TestCase):
    """The user, 2026-11-17: Project Officer yes (not Senior); Remote Feed Operator yes; Trades Assistant and
    Construction Materials Tester no."""
    def test_choices(self):
        from hcb import targets
        self.assertEqual(targets.match_title("Remote Feed Operator")["group"], "E")
        self.assertTrue(targets.triage("Project Officer", "Hobart")["read_detail"])
        for t in ("Senior Project Officer", "Trades Assistant", "Construction Materials Tester (Asphalt)"):
            self.assertFalse(targets.triage(t, "Hobart")["read_detail"], t)


class UserTitleChoices2(unittest.TestCase):
    def test_maintainer_dispatcher_customer_service_out(self):
        from hcb import targets
        for t in ("Mechanical Maintainer", "Emergency Medical Dispatcher (510695)",
                  "Service Tasmania - Customer Service Consultant"):
            self.assertFalse(targets.triage(t, "Hobart")["read_detail"], t)
        for t in ("Maintenance Planner", "Dispatch Coordinator", "Technical Officer"):   # targets still pass
            self.assertTrue(targets.triage(t, "Hobart")["read_detail"], t)
