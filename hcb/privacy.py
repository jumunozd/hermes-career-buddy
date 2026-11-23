"""Leak guard for the public repository (P-5). No LLM, no network.

Fails when a file that git would publish contains personal data of the candidate:
- values from private/facts (phone, email, places, employers, referees; the name outside author files),
- extra terms listed one per line in private/privacy-terms.txt,
- generic patterns: e-mail addresses, Australian phone numbers, long numeric ids, token-like strings.
Matches are reported masked, so the scan output itself never leaks the value.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .util import ROOT, load_yaml, private_dir

# The author's name may appear only where a portfolio project names its author.
NAME_ALLOWED = {"README.md", "LICENSE"}
# Place names may appear where the project lists Tasmanian geography (zones), never next to the candidate.
GEOGRAPHY_FILES = {"config/sources.yaml", "config/job-targets.yaml", "knowledge/specs/job-hunter.md"}
# tests/ hold synthetic contacts (fake phones, example e-mails) to exercise the parsers; private facts and
# the name are still checked there.
SYNTHETIC_PREFIXES = ("tests/",)
# Lock files carry integrity hashes, not secrets.
NO_TOKEN_CHECK = {"package-lock.json"}
# Too generic to be personal in a Tasmanian job-search project.
GENERIC = {"tasmania", "australia", "chile", "santiago", "ireland", "germany", "amazon", "hays", "hobart",
           "launceston", "australian", "full-time", "part-time", "casual", "yes", "no", "none"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_OK = re.compile(r"(?i)(@(example\.(com|org)|anthropic\.com|users\.noreply\.github\.com)$"
                      r"|^(recruitment|careers|jobs|hr|info|enquiries|talent|people)@)")   # employer role inboxes are public
PHONE = re.compile(r"(?<![\d.-])(?:\+?61\s?\(?0?|\(?0)[2-478]\)?(?: ?\d){8}(?![\d-])")
FAKE_PHONE = re.compile(r"^\(?(?:\+?61\s?|0)[2-478]\)? ?0{2,}")
LONG_ID = re.compile(r"(?<![\w-])\d{9,12}(?![\w-])")          # Telegram / account ids
TOKEN = re.compile(r"(?<![A-Za-z0-9])(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{32}(?![A-Za-z0-9])")
TEXT_SUFFIX = {".md", ".py", ".yaml", ".yml", ".json", ".txt", ".js", ".sh", ".toml", ".cfg", ".html", ".csv", ""}


def _strings(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)
    elif isinstance(x, (str, int)):
        yield str(x)


def private_terms(root: Path | None = None) -> tuple[set[str], set[str]]:
    """(terms, name_terms) from the private facts. Empty when only the synthetic persona exists."""
    root = root or private_dir()
    facts = root / "facts"
    terms, names, places = set(), set(), set()
    if not (facts / "identity.yaml").exists() or "examples" in root.parts:
        return terms, names
    ident = load_yaml(facts / "identity.yaml")
    name = ident.get("name_on_documents", "")
    names |= {name, *name.split(), *(ident.get("name_never") or [])}
    for key in ("phone", "email"):
        if ident.get(key):
            terms.add(str(ident[key]))
    for seg in re.split(r"[,;|()]", str(ident.get("location_line", ""))):
        places.add(seg.strip())
    roles = load_yaml(facts / "roles.yaml")
    for r in roles.get("roles", []):
        for key in ("employer_display", "legal_employer", "employer_on_forms", "location", "project_name", "venture"):
            for seg in re.split(r"[,;|()]|\bassigned to\b", str(r.get(key) or "")):
                seg = seg.strip()
                (places if re.search(r"(?i)\b(mine site|tasmania|chile)\b", seg) or key == "location" else terms).add(seg)
    for s in _strings(roles.get("referees") or []):
        terms.add(s.strip())
    # Real people the system found or the user added (networking contacts): their names never go public.
    import json as _json
    for f in (root / "state" / "research").glob("*/contacts.json"):
        try:
            data = _json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for c in (data.get("contacts") if isinstance(data, dict) else data) or []:
            if isinstance(c, dict) and c.get("name") and len(str(c["name"]).split()) >= 2:
                terms.add(str(c["name"]).strip())
    box = root / "config" / "alerts-mailbox.yaml"
    if box.exists():
        for k, v in (load_yaml(box) or {}).items():
            if isinstance(v, str) and "@" in v:
                terms.add(v.strip())
            elif isinstance(v, dict) and isinstance(v.get("from"), str):
                terms.add(v["from"].strip())
    extra = root / "privacy-terms.txt"
    if extra.exists():
        terms |= {l.strip() for l in extra.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}
    def ok(t):
        return (len(t) >= 4 and t.lower() not in GENERIC and not t.isdigit()
                and not re.fullmatch(r"(?i)(the|and|for|with|family-owned retail business|.*products.*)", t))
    places = {re.sub(r"(?i)\s*mine site$", "", p).strip() for p in places}
    places = {p for p in places if ok(p)}
    terms = terms - places
    global PLACES
    PLACES = places
    clean = {t for t in terms | places if len(t) >= 4 and t.lower() not in GENERIC and not t.isdigit()
             and not re.fullmatch(r"(?i)(the|and|for|with|family-owned retail business|mine site|.*products.*)", t)}
    return clean, {n for n in names if len(n) >= 3}


PLACES: set[str] = set()


def publishable_files() -> list[Path]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard"],
                         capture_output=True, text=True, check=True).stdout.splitlines()
    return [ROOT / f for f in out if "node_modules/" not in f]


def _mask(v: str) -> str:
    return v[:2] + "*" * max(len(v) - 4, 1) + v[-2:] if len(v) > 4 else "****"


def scan(files: list[Path] | None = None, root: Path | None = None) -> list[dict]:
    terms, names = private_terms(root)
    term_rx = [(t, re.compile(r"(?i)(?<![\w])" + re.escape(t) + r"(?![\w])")) for t in sorted(terms, key=len, reverse=True)]
    name_rx = [(n, re.compile(r"(?<![\w])" + re.escape(n) + r"(?![\w])")) for n in sorted(names, key=len, reverse=True)]
    hits = []
    for p in files if files is not None else publishable_files():
        if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIX or p.stat().st_size > 2_000_000:
            continue
        rel = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            found = []
            for t, rx in term_rx:
                if t in PLACES and rel in GEOGRAPHY_FILES:
                    continue
                if rx.search(line):
                    found.append(("private_fact", t))
            if p.name not in NAME_ALLOWED:
                for t, rx in name_rx:
                    if rx.search(line):
                        found.append(("name", t))
            if rel.startswith(SYNTHETIC_PREFIXES):
                for kind, v in found:
                    hits.append({"file": rel, "line": n, "kind": kind, "value": _mask(v)})
                continue
            for m in EMAIL.finditer(line):
                if not EMAIL_OK.search(m.group()):
                    found.append(("email", m.group()))
            for m in PHONE.finditer(line):
                if not FAKE_PHONE.match(m.group()):
                    found.append(("phone", m.group()))
            for m in LONG_ID.finditer(line):
                if m.group().count("0") >= 6:      # placeholder like 0400000000
                    continue
                found.append(("long_id", m.group()))
            for m in (TOKEN.finditer(line) if p.name not in NO_TOKEN_CHECK else ()):
                found.append(("token_like", m.group()))
            for kind, v in found:
                hits.append({"file": rel, "line": n, "kind": kind, "value": _mask(v)})
    return hits
