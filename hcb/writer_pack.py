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
            "source", "confirmed_from_vault", "dashboard_content_source",
            "pending_metrics"}  # unverified numbers never reach the Writer
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


def build(index: bool = False, only_ids: set | None = None) -> str:
    """index (P-16): one line per evidence unit, for writing targets.yaml without loading the 55k-char bank.
    only_ids: full cards for these units only (after `engine select`), for drafting."""
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
        if only_ids is not None:
            items = [e for e in items if e["id"] in only_ids]
            if not items:
                continue
        L.append(f"### role: {role}")
        for e in items:
            if index:
                claim = e["claim"] if len(e["claim"]) <= 110 else e["claim"][:107] + "..."
                L.append(f"- {e['id']} [{e['status']}] {claim} | tags: {_clean(e.get('capabilities'))}"
                         + (" | always_include" if e.get("always_include") else ""))
                continue
            L.append(f"- **{e['id']}** [{e['status']}, {e.get('match_depth_default')}] {e['claim']}"
                     f" | metrics: {_clean(e.get('metrics')) or '-'} | tags: {_clean(e.get('capabilities'))}")
            for k, v in e.items():
                if k not in _EV_SKIP and v not in (None, "", []):
                    L.append(f"  - {k}: {_clean(v)}")
        L.append("")
    return "\n".join(L) + "\n"


def write_index() -> dict:
    """private/writer/facts-index.md: identity, roles, prohibitions, credentials + a one-line evidence index."""
    text = build(index=True)
    out = _out().with_name("facts-index.md")
    out.write_text(text, encoding="utf-8")
    return {"path": str(out), "chars": len(text)}


def write_selected(folder) -> dict:
    """<folder>/facts-selected.md: full cards of the units `engine select` put IN, the always_include units and the
    project cards; a statement plan keeps the whole bank (a STAR case may use evidence the CV left out)."""
    import json
    from pathlib import Path
    folder = Path(folder)
    plan = json.loads((folder / "document-plan.json").read_text(encoding="utf-8")) if (folder / "document-plan.json").exists() else {}
    if any(str(d.get("type", "")).lower() in ("selection_criteria", "statement", "short_form_application")
           for d in plan.get("documents", [])):
        text, ids = build(), None
    else:
        sel = json.loads((folder / "selection.json").read_text(encoding="utf-8"))
        ids = {i for u in sel.get("units", []) for i in u.get("ids", [])}
        ev = load_yaml(facts_root() / "facts/evidence.yaml")["evidence"]
        ids |= {e["id"] for e in ev if e.get("always_include") or e["id"].startswith("project_")}
        text = build(only_ids=ids)
    out = folder / "facts-selected.md"
    out.write_text(text, encoding="utf-8")
    return {"path": str(out), "chars": len(text), "units": None if ids is None else len(ids)}


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
