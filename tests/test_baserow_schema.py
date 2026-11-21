"""P-6 schema v2 migration: additive plan, interactive-only apply, login never leaves memory."""
import unittest
from unittest import mock

from hcb import baserow_schema

LIVE = [{"id": 7902, "name": "Status", "type": "multiple_select",
         "select_options": [{"id": 1, "value": "Discovered", "color": "blue"}]},
        {"id": 7898, "name": "Job Title", "type": "text"},
        {"id": 9000, "name": "Fit", "type": "text"}]          # pre-existing with another type: left alone


class Tty:
    def __init__(self, tty): self.tty = tty
    def isatty(self): return self.tty


class SchemaV2(unittest.TestCase):
    def test_plan_is_additive(self):
        p = baserow_schema.plan(LIVE)
        names = [f["name"] for f in p["create_fields"]]
        self.assertIn("Opportunity Ref", names); self.assertNotIn("Fit", names)
        self.assertEqual(p["add_status_options"], ["Closed"])
        self.assertTrue(any("Fit" in c for c in p["conflicts"]))
        sel = next(f for f in p["create_fields"] if f["name"] == "Ranking Category")
        self.assertEqual([o["value"] for o in sel["select_options"]][0], "principal")

    def test_apply_refuses_without_a_terminal(self):
        with self.assertRaises(PermissionError):
            baserow_schema.apply(stdin=Tty(False))

    def test_apply_creates_fields_and_keeps_existing_options(self):
        calls = []
        def req(method, path, jwt, body=None):
            calls.append((method, path, jwt, body))
            return {"access_token": "J"} if path == "/api/user/token-auth/" else {}
        with mock.patch("hcb.baserow.live_schema", return_value=LIVE), \
             mock.patch("hcb.baserow_schema.plan_tables", return_value=[]):
            out = baserow_schema.apply(stdin=Tty(True), ask=lambda _: "user@example.com",
                                       ask_secret=lambda _: "s3cret", request=req)
        self.assertEqual(calls[0][3], {"email": "user@example.com", "password": "s3cret"})
        self.assertTrue(all(c[2] == "J" for c in calls[1:]))
        patch = [c for c in calls if c[0] == "PATCH"][0]
        self.assertEqual([o["value"] for o in patch[3]["select_options"]], ["Discovered", "Closed"])
        self.assertEqual(patch[3]["select_options"][0]["id"], 1)          # existing option kept by id
        self.assertNotIn("s3cret", str(out)); self.assertNotIn("'J'", str(out))
        self.assertFalse([c for c in calls if c[0] == "DELETE"])


class TablesP7(unittest.TestCase):
    def test_empty_tables_get_every_field_including_links(self):
        plans = {t["table"]: t for t in baserow_schema.plan_tables({"documents": [], "contacts": [
            {"id": 1, "name": "Channel", "type": "single_select", "select_options": [{"id": 9, "value": "LinkedIn", "color": "blue"}]}]})}
        docs = {f["name"]: f for f in plans["documents"]["create_fields"]}
        self.assertEqual(docs["Application"]["link_row_table_id"], 839)
        self.assertFalse(docs["Application"]["has_related_field"])
        self.assertEqual(docs["Approved"]["type"], "boolean")
        ch = plans["contacts"]["add_options"][0]
        self.assertEqual(ch["field"], "Channel"); self.assertNotIn("LinkedIn", ch["add"]); self.assertIn("Phone (ad)", ch["add"])


if __name__ == "__main__":
    unittest.main()
