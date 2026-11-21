"""P-6: opportunity -> Baserow fields; only non-discarded offers; duplicates skipped."""
import unittest

from hcb import registry

OPP = {"title": "Project Officer", "employer": "Acme", "location": "Hobart", "ranking_category": "principal",
       "url": "https://careers.jobs.tas.gov.au/jobs/project-officer-1", "closing_date": "2026-12-01",
       "discovered_at": "2026-11-19T07:30:00+11:00", "ad_text": "Contact Alex Example on 0400 000 000."}
IDS = lambda name: {"Status": {"Discovered": 1, "Preparing": 2}, "Ranking Category": {"principal": 3},
                    "Alignment Group": {"C": 4, "none": 5}, "Source": {"TSS": 6, "SEEK (pasted)": 7},
                    "Entry Signal": {"Neutral": 8}}.get(name, {})


class Registry(unittest.TestCase):
    def test_fields(self):
        f = registry.fields_for(OPP)
        self.assertEqual((f["Alignment Group"], f["Source"], f["Discovered"], f["Status"]), ("C", "TSS", "2026-11-19", "Discovered"))
        self.assertEqual(f["Ad Contact"], "Alex Example: 0400 000 000")
        self.assertTrue(f["Opportunity Ref"].startswith("o-")); self.assertIn("[hcb v1]", f["Notes"])

    def test_only_kept_offers(self):
        self.assertTrue(registry.kept(OPP, "2026-11-19"))
        self.assertFalse(registry.kept({**OPP, "title": "Senior Project Officer"}, "2026-11-19"))
        self.assertFalse(registry.kept({**OPP, "closing_date": "2026-11-01"}, "2026-11-19"))
        self.assertFalse(registry.kept({**OPP, "title": "Registered Nurse"}, "2026-11-19"))
        self.assertFalse(registry.kept(OPP, "2026-11-19", {"Project Officer"}))

    def test_preview_skips_duplicates(self):
        f = registry.fields_for(OPP)
        live = [{"Opportunity Ref": f["Opportunity Ref"]}]
        p = registry.preview([f], live_rows=live, option_ids=IDS)
        self.assertTrue(p[0]["duplicate"]); self.assertIsNone(p[0]["payload"])
        p2 = registry.preview([f], live_rows=[], option_ids=IDS)
        self.assertEqual(p2[0]["payload"]["Alignment Group"], 4)


if __name__ == "__main__":
    unittest.main()


class Register(unittest.TestCase):
    def test_registers_only_kept_once_and_writes_ids_back(self):
        import json, tempfile
        from pathlib import Path
        snap = {"opportunities": [OPP, {**OPP, "title": "Senior Project Officer", "url": "https://x.example/2"}]}
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "s.json"; f.write_text(json.dumps(snap))
            calls = []
            def writer(kind, fields, key, live, task_id):
                calls.append(fields["Opportunity Ref"])
                return {"write_performed": True, "row_id": 41, "verified": True}
            out = registry.register_snapshot(f, "2026-11-19", live=True, live_rows=[], writer=writer, option_ids=IDS)
            saved = json.loads(f.read_text())
            again = registry.register_snapshot(f, "2026-11-19", live=True, live_rows=[], writer=writer, option_ids=IDS)
        self.assertEqual(len(calls), 1)
        self.assertEqual(saved["opportunities"][0]["baserow_id"], 41)
        self.assertEqual([r["action"] for r in out["results"]], ["created", "not_registered"])
        self.assertEqual([r["action"] for r in again["results"]], ["not_registered"])


class P7(unittest.TestCase):
    def test_document_rows_from_a_version(self):
        import json, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            v = Path(tmp) / "acme" / "prep-001" / "v2"; v.mkdir(parents=True)
            (v / "cv-alex-example.pdf").write_bytes(b"%PDF"); (v / "cover-letter.pdf").write_bytes(b"%PDF")
            (v / "notes.pdf").write_bytes(b"%PDF")
            (v / "manifest.json").write_text(json.dumps({"files": [{"file": "cv-alex-example.pdf", "sha256": "abc"}]}))
            rows = registry.document_rows(v, "REF-1", "Acme", 26)
        self.assertEqual(sorted(r["Document Type"] for r in rows), ["CV", "Cover letter"])
        cv = next(r for r in rows if r["Document Type"] == "CV")
        self.assertEqual((cv["SHA256"], cv["Version"], cv["Package Version"], cv["Application"]), ("abc", 2, "prep-001/v2", 26))

    def test_contact_rows_dedupe_and_no_approach(self):
        rows = registry.contact_rows("Contact Alex Example on 0400 000 000 or careers@acme.example.com", "Acme", 26,
                                     research=[{"name": "Canal", "professional_email": "careers@acme.example.com",
                                                "email_status": "verified_public_business", "confidence": "confirmed"}],
                                     no_approach=True)
        self.assertEqual([r["Name"] for r in rows], ["Alex Example"])   # the person; inboxes are not contacts
        self.assertTrue(all(r["Approach"] == "no-approach clause" for r in rows))

    def test_write_p7_skips_existing(self):
        calls = []
        w = lambda table, kind, f, key, live, task_id: calls.append(table) or {"mode": "dry_run"}
        out = registry.write_p7({"documents": [{"_file": "x.pdf", "Document Name": "CV", "SHA256": "abc"}],
                                 "contacts": [{"Name": "A", "Phone": "0400 000 000", "Application": 26}]},
                                live=False, existing_docs=[{"SHA256": "abc"}],
                                existing_contacts=[{"Phone": "0400 000 000", "Application": [{"id": 26}]}], writer=w)
        self.assertEqual(calls, [])
        self.assertEqual([x["action"] for x in out["documents"] + out["contacts"]], ["already_in_baserow"] * 2)


class OnePersonOneContact(unittest.TestCase):
    def test_phone_and_email_of_one_person_merge(self):
        rows = registry.contact_rows("", "Acme", 27, contacts={"contact_names": ["Alex Example"],
                                     "phones": [{"raw": "0400 000 000"}], "emails": ["alex@example.com"]})
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["Phone"], rows[0]["Email"], rows[0]["Channel"]), ("0400 000 000", "alex@example.com", "Phone (ad)"))


class ContactsArePeople(unittest.TestCase):
    """The user, 2026-11-19: Contacts is a database of people to contact; application inboxes live in Applications."""
    def test_inboxes_go_to_ad_contact_not_contacts(self):
        o = {**OPP, "ad_text": "Apply via careers@acme.example.com. Questions: Sam Lee on 0400 000 001."}
        self.assertEqual(registry.contact_rows(o["ad_text"], "Acme", 26), [
            {"Name": "Sam Lee", "Company": "Acme", "Channel": "Phone (ad)", "Phone": "0400 000 001",
             "Confidence": "confirmed", "Origin": "Ad", "Approach": "allowed", "Application": 26}])
        self.assertIn("Postulación: careers@acme.example.com", registry.fields_for(o)["Ad Contact"])
        self.assertEqual(registry.contact_rows("Email recruitment@acme.example.com", "Acme", 26), [])

