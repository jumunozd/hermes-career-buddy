"""Where the candidate's private facts live, and the name used on documents.

Hermes Career Buddy keeps personal data in `private/` (gitignored). `HCB_PRIVATE_DIR` overrides it;
without a `private/facts/` folder the synthetic persona in `examples/candidate/` is used, so the public
repository runs as a demo.
"""
import os
import re
import unicodedata
from pathlib import Path

import yaml

ENGINE = Path(__file__).resolve().parent.parent
PROJECT = ENGINE.parent


def private_dir() -> Path:
    env = os.environ.get("HCB_PRIVATE_DIR")
    if env:
        return Path(env).expanduser().resolve()
    p = PROJECT / "private"
    return p if (p / "facts").is_dir() else PROJECT / "examples" / "candidate"


FACTS = private_dir() / "facts"


def identity() -> dict:
    return yaml.safe_load((FACTS / "identity.yaml").read_text(encoding="utf-8")) or {}


def slug(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


NAME = identity().get("name_on_documents", "Candidate")
NAME_NEVER = identity().get("name_never") or []
CV_STEM = "cv-" + slug(NAME)
