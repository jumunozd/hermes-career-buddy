"""Generate the Writer's facts digest from the Job Application Engine (read-only).

One structured file instead of five YAML files read separately. It is GENERATED, never
edited by hand, and stamped with the SHA256 of each source, so a stale digest is detected
(`bin/hcb writer-pack --check`) and the Engine stays the single source of truth.
Referee contact details are deliberately left out (only used when a portal asks).
"""
from __future__ import annotations

import re

from .util import facts_root, load_yaml, now_iso, private_dir, sha256_file

def _out():
    return private_dir() / "writer" / "facts-digest.md"


SOURCES = ["facts/identity.yaml", "facts/roles.yaml", "facts/prohibitions.yaml",
           "facts/credentials.yaml", "facts/evidence.yaml"]
# Evidence keys already shown in the headline row, or pure provenance with no writing value.
_EV_SKIP = {"id", "role", "claim", "metrics", "capabilities", "match_depth_default", "status",
            "source", "confirmed_from_vault", "dashboard_content_source"}
_ROLE_SKIP = {"id", "title_on_documents", "employer_display", "display_dates", "block", "referee"}


def _clean(v) -> str:
    if isinstance(v, (list, tuple)):
        return "; ".join(_clean(x) for x in v)
    if isinstance(v, dict):
        return "; ".join(f"{k}={_clean(x)}" for k, x in v.items())
    return re.sub(r"\s+", " ", str(v)).strip()


def source_hashes() -> dict:
    root = facts_root()
    return {s: sha256_file(root / s) for s in SOURCES}


def build() -> str:
    root = facts_root()
    ident = load_yaml(root / "facts/identity.yaml")
    roles = load_yaml(root / "facts/roles.yaml")
    proh = load_yaml(root / "facts/prohibitions.yaml")
    creds = load_yaml(root / "facts/credentials.yaml")["credentials"]
    evidence = load_yaml(root / "facts/evidence.yaml")["evidence"]
    hashes = source_hashes()

    L = ["# Facts digest (GENERATED: do not edit; regenerate with `bin/hcb writer-pack`)", "",
         f"Generated {now_iso()} from the Job Application Engine. Authority: the Engine `facts/`.",
         "Source SHA256 (first 16):"]
    L += [f"- `{s}` {h[:16]}" for s, h in hashes.items()]
    L += ["", "Use: copy titles, employers, dates and claims LITERALLY. A claim may be shortened, never",
          "inflated. Cite evidence ids in content.json bullets. `context_only` units are background,",
          "never a CV bullet. Anything not in this file does not exist for the Writer.", ""]

    L += ["## Identity (header and contact lines)"]
    for k, v in ident.items():
        L.append(f"- {k}: {_clean(v)}")

    eo = roles.get("experience_order", {})
    L += ["", "## Roles (titles, employers, dates: literal)",
          f"Order of blocks: {_clean(eo.get('blocks'))}. Within a block: {_clean(eo.get('within_block'))}",
          f"Headings: {_clean(eo.get('headings'))}", ""]
    for r in roles["roles"]:
        L.append(f"### {r['id']} [{r.get('block')}] {r.get('title_on_documents')} | "
                 f"{r.get('employer_display', r.get('employer_on_forms'))} | {r.get('display_dates', r.get('period', ''))}")
        for k, v in r.items():
            if k not in _ROLE_SKIP and v not in (None, "", []):
                L.append(f"- {k}: {_clean(v)}")
    L += ["", "### Education"]
    for e in roles.get("education_periods", []):
        L.append("- " + "; ".join(f"{k}={_clean(v)}" for k, v in e.items() if k != "id"))
    L += ["", "Referees: kept in the Engine `facts/roles.yaml`; include only if the ad/portal asks. "
          f"Rule: {_clean(roles.get('referee_rule'))}"]

    L += ["", "## Prohibitions (verify.py blocks these)"]
    for p in proh.get("patterns", []):
        L.append(f"- `{p['pattern']}`: {p['reason']}")
    L += ["", "Attribution rules (checked by judgement):"]
    L += [f"- {_clean(a)}" for a in proh.get("attribution_rules", [])]
    L += ["", f"Domain knowledge never claimed: {_clean(proh.get('domain_knowledge_never_claimed'))}"]

    L += ["", "## Credentials (Education / Certifications)"]
    for c in creds:
        line = f"- **{c['id']}**: {c['name']} | {c.get('issuer')} | {c.get('period')}"
        if c.get("metric") not in (None, "", "n/a"):
            line += f" | metric: {_clean(c['metric'])}"
        L.append(line)
        extra = {k: v for k, v in c.items() if k in {"skills", "relevance_tags", "display_rule", "wording_rule",
                                                       "sql_note", "skills_note", "skills_note_2", "kind",
                                                       "licence_class", "pending_edit", "always_include"} and v}
        for k, v in extra.items():
            L.append(f"  - {k}: {_clean(v)}")

    L += ["", "## Evidence bank (one unit per achievement)",
          "Format: id [status, default match depth] claim | metrics | capability tags, then rules.", ""]
    by_role: dict[str, list] = {}
    for e in evidence:
        by_role.setdefault(e["role"], []).append(e)
    for role, items in by_role.items():
        L.append(f"### role: {role}")
        for e in items:
            L.append(f"- **{e['id']}** [{e['status']}, {e.get('match_depth_default')}] {e['claim']}"
                     f" | metrics: {_clean(e.get('metrics')) or '-'} | tags: {_clean(e.get('capabilities'))}")
            for k, v in e.items():
                if k not in _EV_SKIP and v not in (None, "", []):
                    L.append(f"  - {k}: {_clean(v)}")
        L.append("")
    return "\n".join(L) + "\n"


def write() -> dict:
    text = build()
    OUT = _out()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    return {"path": str(OUT), "chars": len(text), "sources": source_hashes()}


def check() -> dict:
    """Fresh = every source hash recorded in the digest equals the Engine file now."""
    OUT = _out()
    if not OUT.exists():
        return {"fresh": False, "reason": "digest missing"}
    text = OUT.read_text(encoding="utf-8")
    stale = [s for s, h in source_hashes().items() if f"`{s}` {h[:16]}" not in text]
    return {"fresh": not stale, "stale_sources": stale}
