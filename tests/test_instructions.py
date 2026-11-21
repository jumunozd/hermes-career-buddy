"""Executable instructions must match the real CLI (Hermes review 2026-11-17: schedules called a missing
`bin/hcb report build`)."""
import re
import subprocess
import unittest

from hcb import util

FILES = [util.ROOT / "config" / "schedules.yaml", util.ROOT / "AGENTS.md",
         *sorted((util.ROOT / ".hermes" / "skills").rglob("*.md"))]


def cli_commands() -> set:
    out = subprocess.run([str(util.ROOT / "bin" / "hcb"), "--help"], capture_output=True, text=True).stdout
    m = re.search(r"\{([a-z0-9,-]+)\}", out)
    return set(m.group(1).split(","))


class Instructions(unittest.TestCase):
    def test_every_named_hcb_command_exists(self):
        known = cli_commands()
        self.assertIn("daily-delivered", known)
        bad = []
        for f in FILES:
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                for cmd in re.findall(r"bin/hcb ([a-z][a-z0-9-]*)", line):
                    if cmd not in known:
                        bad.append(f"{f.relative_to(util.ROOT)}:{n}: bin/hcb {cmd}")
        self.assertEqual(bad, [])

    def test_report_subcommand_takes_a_snapshot(self):
        sched = (util.ROOT / "config" / "schedules.yaml").read_text(encoding="utf-8")
        self.assertNotIn("report build", sched)
        self.assertIn("bin/hcb report <", sched)


if __name__ == "__main__":
    unittest.main()
