"""Test package. Tests must never write to the real Baserow (2026-11-19: a test wrote row 31)."""
import os

os.environ["HCB_NO_LIVE_WRITES"] = "1"
