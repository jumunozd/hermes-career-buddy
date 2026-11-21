"""Status page and pipeline board (P-13): read-only, offline HTML, never crashes on missing inputs."""
import json
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from hcb import util

NOW = datetime.fromisoformat("2026-11-24T12:40:00+11:00")
ROWS = [
    {"id": 1, "Job Title": "Asset Management Officer", "Company": "Example Water", "Location": "Hobart",
     "Status": "Ready for Review", "Closing Date": "2026-11-26", "Alignment Group": "A", "Job URL": "https://example.com/1"},
    {"id": 2, "Job Title": "Production Planner <script>", "Company": "Acme Foods", "Location": "Launceston",
     "Status": "Discovered", "Closing Date": "2026-11-30", "Alignment Group": "C", "Job URL": "javascript:alert(1)",
     "Discovered": "2026-11-23"},
    {"id": 3, "Job Title": "Project Officer", "Company": "Council", "Location": "Glenorchy", "Status": "Applied",
     "Date applied": "2026-11-20", "Next Follow Up": "2026-11-24"},
    {"id": 4, "Job Title": "Old", "Company": "X", "Status": "Closed"},
]
JOBS = [
    {"name": "jh-weekday-search-and-digest", "last_run_at": "2026-11-24T12:30:00+11:00", "last_status": "ok",
     "next_run_at": "2026-11-24T16:30:00+11:00"},
    {"name": "daily-backup", "last_run_at": "2026-11-22T03:00:00+11:00", "last_status": "ok",
     "next_run_at": "2026-11-23T03:00:00+11:00"},          # missed: next run is in the past
    {"name": "reminder-old", "last_run_at": "2026-11-18T08:00:00+11:00", "last_status": "ok", "next_run_at": None},
]


class Dashboard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg = dict(util.config()); cfg["paths"] = {**cfg["paths"], "state": self.tmp.name, "reports": self.tmp.name}
        self.p = mock.patch.object(util, "config", return_value=cfg)
        self.p.start()
        from hcb import state
        state.event("backup", archive="hcb-backup-x.tar.enc", verified=True)

    def tearDown(self):
        self.p.stop(); self.tmp.cleanup()

    def test_model(self):
        from hcb import dashboard
        m = dashboard.build(NOW, rows=ROWS, jobs=JOBS, use_live=False)
        self.assertEqual([r["id"] for r in m["ready"]], [1])
        self.assertEqual([r["id"] for r in m["closing"]], [1, 2])         # Applied rows are not "closing"
        self.assertEqual([r["id"] for r in m["followups"]], [3])
        self.assertEqual(m["final_counts"]["Closed"], 1)
        names = {j["name"]: j["status"] for j in m["jobs"]}
        self.assertEqual(len(names), 2)                                   # finished one-off reminder hidden
        self.assertEqual(names["Respaldo diario 03:00"], "atrasada")

    def test_html_is_offline_and_escaped(self):
        from hcb import dashboard
        res = dashboard.write(NOW, rows=ROWS, jobs=JOBS, use_live=False)
        page = Path(res["file"]).read_text()
        self.assertNotIn("<script>", page)                                # titles escaped, no scripts at all
        self.assertNotIn("javascript:", page)                             # only https ad links are rendered
        self.assertIn("default-src 'none'", page)                         # CSP: nothing loads from the web
        external = set(re.findall(r'(?:src|href)="(https?://[^"]+)"', page))
        self.assertEqual(external, {"https://example.com/1"})
        self.assertEqual(Path(res["file"]).stat().st_mode & 0o777, 0o600)

    def test_missing_inputs_render(self):
        from hcb import dashboard
        res = dashboard.write(NOW, rows=None, jobs=None, use_live=False)
        page = Path(res["file"]).read_text()
        self.assertIn("Baserow no responde", page)
        self.assertIn("No se pudo leer la lista de tareas", page)
        self.assertIn("Baserow no responde", res["summary"])

    def test_summary(self):
        from hcb import dashboard
        s = dashboard.summary(dashboard.build(NOW, rows=ROWS, jobs=JOBS, use_live=False))
        self.assertIn("Por revisar: 1", s)
        self.assertIn("revisar Respaldo diario", s)

    def test_refresh_never_runs_under_tests(self):
        from hcb import dashboard
        with mock.patch.object(dashboard, "write", side_effect=AssertionError("must not run")):
            dashboard.refresh_quietly()


if __name__ == "__main__":
    unittest.main()
