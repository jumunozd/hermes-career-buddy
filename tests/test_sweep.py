"""Deterministic listing sweep (RT-14b): card parsing, paging, Seen + triage, no LLM."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from hcb import util

NOW = datetime.fromisoformat("2026-11-17T07:30:00+11:00")   # Tuesday

TSS_PAGE = """Displaying **1-2** of **3** in total

### [Government Business Analyst (724626)](https://careers.jobs.tas.gov.au/jobs/government-business-analyst-724626-south-tas-australia)

*    South
*    Analyst
*    Closing at: 29 Nov 2026 - 11:55pm AEDT
*    Tasmanian State Service Award - General Stream Band 6
*    Department of Treasury and Finance
*    $110,000

[Read more](https://careers.jobs.tas.gov.au/jobs/government-business-analyst-724626-south-tas-australia)

### [Registered Nurse (502371L2)](https://careers.jobs.tas.gov.au/jobs/registered-nurse-502371l2-north-west-tas-australia)

*    North West
*    Closing at: 1 Dec 2026 - 11:55pm AEDT
"""
TSS_PAGE2 = """### [Manager Budget Development (724791)](https://careers.jobs.tas.gov.au/jobs/manager-budget-development-724791-south-tas-australia)

*    South
*    Closing at: 2 Dec 2026 - 11:55pm AEDT
"""
GLENORCHY = """## Vacancies at Glenorchy City Council

#### Multi-Skilled Labourer - Civil

Closes Nov 22, 2026

#### [Find out more/apply](https://jobs.gcc.tas.gov.au/job-details/query/Multi-Skilled+Labourer/in/Australia/9842968/)"""
HUON = """## [Remote Feed Operator](https://www.huonaqua.com.au/careers/current-jobs/#job-493877)

Location Hobart Applications Close 11:55pm Friday, 27 Nov 2026
## [Farm Attendant - Bath Crew](https://www.huonaqua.com.au/careers/current-jobs/#job-493868)

Location Dover"""


class SweepTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg = dict(util.config()); cfg["paths"] = {**cfg["paths"], "state": self.tmp.name, "reports": self.tmp.name, "applications": self.tmp.name}
        self.p = mock.patch.object(util, "config", return_value=cfg)
        self.p.start()

    def tearDown(self):
        self.p.stop(); self.tmp.cleanup()

    def test_parse_tss_cards(self):
        from hcb import sweep
        cards = sweep.parse_cards(TSS_PAGE, r"careers\.jobs\.tas\.gov\.au/jobs/(?!search)[a-z0-9-]+-\d", "TSS")
        self.assertEqual([c["title"] for c in cards], ["Government Business Analyst (724626)", "Registered Nurse (502371L2)"])
        ba = cards[0]
        self.assertEqual((ba["location"], ba["zone"]["status"], ba["closing"], ba["company"]),
                         ("South", "region_only", "2026-11-29", "Department of Treasury and Finance"))

    def test_heading_title_and_mdy_closing(self):
        from hcb import sweep
        c = sweep.parse_cards(GLENORCHY, r"jobs\.gcc\.tas\.gov\.au/job-details/", "Glenorchy City Council")[0]
        self.assertEqual((c["title"], c["closing"]), ("Multi-Skilled Labourer - Civil", "2026-11-22"))

    def test_huon_location_and_close(self):
        from hcb import sweep
        cs = sweep.parse_cards(HUON, r"huonaqua\.com\.au/careers/current-jobs/#job-\d+", "Huon Aquaculture")
        self.assertEqual([(c["zone"]["status"], c["closing"]) for c in cs], [("in_zone", "2026-11-27"), ("out_of_zone", "")])

    def _fake_read(self, pages):
        calls = []
        def read(sid, url=None):
            calls.append((sid, url))
            text = pages.get((sid, url), "no current vacancies")
            f = Path(self.tmp.name) / f"{sid}-{len(calls)}.md"
            f.write_text(text, encoding="utf-8")
            return {"ok": True, "file": str(f)}
        return read, calls

    def test_sweep_pages_seen_and_triage(self):
        from hcb import sweep
        reg = [{"id": "SRC-01", "name": "TSS", "mode": "page_read", "enabled": True, "cadence": "every_run",
                "url": "https://careers.jobs.tas.gov.au/cw/en/listing/",
                "job_link": r"careers\.jobs\.tas\.gov\.au/jobs/(?!search)[a-z0-9-]+-\d",
                "pages": "https://careers.jobs.tas.gov.au/jobs/search?page={n}", "title_filter": "strict"}]
        pages = {("SRC-01", None): TSS_PAGE, ("SRC-01", "https://careers.jobs.tas.gov.au/jobs/search?page=2"): TSS_PAGE2}
        read, calls = self._fake_read(pages)
        with mock.patch("hcb.sources.registry", return_value=reg):
            out = sweep.sweep(NOW, read=read)
            st = out["per_source"][0]
            self.assertEqual(st["pages_read"], 2)
            self.assertEqual([s["title"] for s in out["shortlist"]], ["Government Business Analyst (724626)"])
            self.assertEqual(st["logged_by_title"], 2)           # nurse + budget manager, from the card only
            # second run: the logged cards are known; the shortlisted one is new until the Job Hunter adds it
            read2, calls2 = self._fake_read(pages)
            out2 = sweep.sweep(NOW, read=read2)
            self.assertEqual(out2["per_source"][0]["known_unchanged"], 2)
            self.assertEqual(len(out2["shortlist"]), 1)

    def test_heading_cards(self):  # P-12: whole ads under headings, no link per job (Shaw)
        from hcb import sweep
        page = ("## Current Employment Opportunities\n#### Project Coordinator\nLocation: Launceston\n"
                "Applications close 30 November 2026\n[Seek](https://au.seek.com/job/1)\n#### Plant Operator\nHobart\n")
        cs = sweep.parse_heading_cards(page, 4, "https://example.com/careers/", "Example Civil")
        self.assertEqual([c["title"] for c in cs], ["Project Coordinator", "Plant Operator"])
        self.assertEqual(cs[0]["url"], "https://example.com/careers/#project-coordinator")
        self.assertEqual(cs[0]["zone"]["status"], "in_zone")

    def test_unparsed_source_goes_to_agent(self):
        from hcb import sweep
        reg = [{"id": "EMP-BELLBAY", "name": "Bell Bay", "mode": "page_read", "enabled": True, "cadence": "every_run",
                "url": "https://bellbayaluminium.com.au/careers"}]
        read, _ = self._fake_read({("EMP-BELLBAY", None): "Careers at Bell Bay ... see Workday"})
        with mock.patch("hcb.sources.registry", return_value=reg):
            out = sweep.sweep(NOW, read=read)
        self.assertEqual(out["needs_agent"][0]["source"], "EMP-BELLBAY")

    def test_registry_parsers_compile(self):
        import re
        from hcb import sources
        for s in sources.registry():
            if s.get("job_link"):
                re.compile(s["job_link"])


if __name__ == "__main__":
    unittest.main()
