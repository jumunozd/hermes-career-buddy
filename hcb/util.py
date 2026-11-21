"""Shared helpers: project paths, config loading, hashing, safe writes. Stdlib + YAML only."""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_yaml_text(text: str):
    try:
        import yaml  # PyYAML (system python3)
        return yaml.safe_load(text)
    except ImportError:
        from ruamel.yaml import YAML  # Hermes venv python
        return YAML(typ="safe", pure=True).load(text)


def load_yaml(path) -> dict:
    return load_yaml_text(Path(path).read_text(encoding="utf-8")) or {}


_CONFIG = None


def config() -> dict:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = load_yaml(ROOT / "config" / "system.yaml")
    return _CONFIG


def mapping() -> dict:
    return load_yaml(ROOT / "config" / "baserow-mapping.yaml")


def private_dir() -> Path:
    """The private zone (P-5): personal facts, applications, state, reports. Gitignored.
    HCB_PRIVATE_DIR overrides; without private/facts the synthetic examples/candidate persona is used."""
    env = os.environ.get("HCB_PRIVATE_DIR")
    if env:
        return Path(env).expanduser().resolve()
    p = ROOT / config()["paths"]["private"]
    return p if (p / "facts").is_dir() else ROOT / "examples" / "candidate"


def is_demo() -> bool:
    """True when running on the synthetic examples/candidate persona (no private zone)."""
    return "examples" in private_dir().parts


def project_path(key: str) -> Path:
    """Writable areas (applications, reports, state), resolved under the private zone."""
    p = private_dir() / config()["paths"][key]
    p.mkdir(parents=True, exist_ok=True)
    return p


def engine_dir() -> Path:
    """Public CV method and build scripts, copied from the Job Application Engine (P-5)."""
    return ROOT / "engine"


def facts_root() -> Path:
    """Folder holding facts/ (identity, roles, evidence, credentials, prohibitions)."""
    return private_dir()


def cv_stem() -> str:
    """CV file stem from the name on documents, e.g. cv-alex-example."""
    name = load_yaml(facts_root() / "facts" / "identity.yaml").get("name_on_documents", "Candidate")
    return "cv-" + re.sub(r"[^a-z0-9]+", "-", fold(name)).strip("-")


def authority_path(key: str) -> Path:
    """Private, read-only inputs (A-H evaluator, Baserow token). Relative paths resolve in the private zone."""
    p = Path(os.path.expanduser(config()["paths"][key]))
    return p if p.is_absolute() else private_dir() / p


def now_iso() -> str:
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo(config()["timezone"])).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def stable_key(*parts) -> str:
    """Idempotency key from real identifiers (Master §4.3)."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def fold(text: str) -> str:
    """Case- and accent-insensitive comparison form (project-manager.md §6.2 rule 1)."""
    nfkd = unicodedata.normalize("NFKD", text or "")
    return re.sub(r"\s+", " ", "".join(c for c in nfkd if not unicodedata.combining(c))).strip().lower()


def write_new(path, text: str) -> Path:
    """Create a file exclusively. Published versions are never overwritten (writer.md §6.6)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def dump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False, default=str) + "\n"


def redact(text: str) -> str:
    """Sanitise messages before logging (Master §6.8, §9.3)."""
    text = re.sub(r"(?i)(token|authorization|api[_-]?key|password)\s*[:=]\s*\S+", r"\1=<redacted>", str(text))
    return re.sub(r"\b[A-Za-z0-9]{32,}\b", "<redacted>", text)
