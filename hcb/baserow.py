"""Baserow adapter for table 839 (Master §6.2, TV-06).

Reads the protected token at ~/.hermes/career-buddy/secrets/baserow-token (moved there from the earlier Baserow integration),
with the same safety posture: loopback URL only, fixed table, no redirects/proxies,
token never printed, logged or placed in argv. Adds what the spec needs and the old
client lacked: paginated reads, duplicate lookup, mapped create/update, Notes tag block.

Writes are DRY-RUN by default. A live write requires ALL of:
  1. config features.baserow_live_writes: true   (set by the user)
  2. an idempotency key not already applied     (state ledger)
  3. explicit --live on the CLI call
Then the row is read back and compared. An uncertain write is never retried blindly.
No delete operation exists. Schema changes are out of scope (migration MIG-01).
"""
from __future__ import annotations

import json
import os
import re
import stat
import urllib.request
from pathlib import Path

from . import state
from .util import authority_path, config, mapping

_TAG_RE = re.compile(r"\[([a-z_]+)=([^\]]*)\]")


class BaserowError(RuntimeError):
    pass


# ---------- Notes tag block (job-hunter.md §6.10 fixed parseable format) ----------
def encode_tags(tags: dict, rest: str = "") -> str:
    m = mapping()["notes_tag_block"]
    unknown = set(tags) - set(m["keys"])
    if unknown:
        raise ValueError(f"unknown tag keys {sorted(unknown)}")
    line = m["prefix"] + "".join(f"[{k}={str(v).replace(']', ')')}]" for k, v in tags.items() if v is not None)
    return line + ("\n" + rest if rest else "")


def decode_tags(notes: str | None) -> tuple[dict, str]:
    notes = notes or ""
    prefix = mapping()["notes_tag_block"]["prefix"]
    first, _, rest = notes.partition("\n")
    if not first.startswith(prefix):
        return {}, notes
    return dict(_TAG_RE.findall(first[len(prefix):])), rest


# ---------- transport ----------
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        raise BaserowError("redirect refused")


def _token() -> str:
    path = Path(os.environ.get("HCB_BASEROW_TOKEN_FILE") or authority_path("baserow_token_file"))
    if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
        raise BaserowError("Token not configured (run the existing setup-token.sh privately).")
    st, dst = path.stat(), path.parent.stat()
    if st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) != 0o600 or stat.S_IMODE(dst.st_mode) != 0o700:
        raise BaserowError("Secret file/dir must be owned by you with 600/700 permissions.")
    tok = path.read_text().strip()
    if not re.fullmatch(r"[A-Za-z0-9]{32}", tok):
        raise BaserowError("Stored token has an invalid format.")
    return tok


def _request(method: str, path: str, body: dict | None = None) -> dict | list:
    m = mapping()
    base = m["base_url"]
    if not re.fullmatch(r"http://(localhost|127\.0\.0\.1):\d+", base):
        raise BaserowError("Only a loopback Baserow URL is allowed.")
    allowed = {m["table_id"], *(t["table_id"] for t in (m.get("tables") or {}).values())}
    if not (path.startswith("/api/database/") and any(f"/table/{t}/" in path for t in allowed)):
        raise BaserowError("Path outside the Career Buddy tables (Applications, Documents, Contacts) refused.")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Authorization", "Token " + _token())
    if data is not None:
        req.add_header("Content-Type", "application/json")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:  # body withheld for safety
        raise BaserowError(f"Baserow returned HTTP {exc.code}; body withheld.") from None
    except urllib.error.URLError:
        raise BaserowError("Local Baserow connection failed; no automatic retry.") from None


# ---------- reads ----------
def live_schema() -> list[dict]:
    return _request("GET", f"/api/database/fields/table/{mapping()['table_id']}/")


def schema_drift() -> list[str]:
    """Contract test: live schema must equal config/baserow-mapping.yaml."""
    expected = mapping()["fields"]
    problems = []
    live = {f["name"]: f for f in live_schema()}
    for name, spec in expected.items():
        f = live.get(name)
        if not f:
            problems.append(f"missing field {name}")
            continue
        if f["type"] != spec["type"]:
            problems.append(f"{name}: type {f['type']} != {spec['type']}")
        if "options" in spec:
            opts = [o["value"] for o in f.get("select_options", [])]
            if opts != spec["options"]:
                problems.append(f"{name}: options changed {opts}")
    for name in set(live) - set(expected):
        problems.append(f"unmapped new field {name}")
    return problems


def list_rows() -> list[dict]:
    rows, page = [], 1
    tid = mapping()["table_id"]
    while True:
        data = _request("GET", f"/api/database/rows/table/{tid}/?user_field_names=true&size=100&page={page}")
        rows.extend(data["results"])
        if not data.get("next"):
            return rows
        page += 1


def get_row(row_id: int) -> dict:
    return _request("GET", f"/api/database/rows/table/{mapping()['table_id']}/{int(row_id)}/?user_field_names=true")


def find_duplicates(candidate: dict, rows: list[dict]) -> dict:
    """Master §3.5: exact URL or source job id -> same vacancy; company+title+location -> possible duplicate."""
    from .util import fold
    url = (candidate.get("Job URL") or "").rstrip("/").lower()
    key = (fold(candidate.get("Company") or ""), fold(candidate.get("Job Title") or ""), fold(candidate.get("Location") or ""))
    same, possible = [], []
    for r in rows:
        if url and (r.get("Job URL") or "").rstrip("/").lower() == url:
            same.append(r["id"])
        elif key[0] and key[1] and (fold(r.get("Company") or ""), fold(r.get("Job Title") or ""), fold(r.get("Location") or "")) == key:
            possible.append(r["id"])
    return {"same_vacancy": same, "possible_duplicates": possible,
            "decision": "update_existing" if same else "flag_possible_duplicate" if possible else "create_new"}


# ---------- payload mapping ----------
WRITABLE = {"Job Title", "Company", "Job URL", "Location", "Status", "Closing Date", "Date applied",
            "Salary", "Next Follow Up", "Notes",
            # P-6 schema v2 (2026-11-19)
            "Opportunity Ref", "Ranking Category", "Alignment Group", "Catalogue Title", "Review Reason",
            "Entry Signal", "Fit", "Source", "Posted Date", "Discovered", "Ad Contact", "Latest Version"}
SELECT_TYPES = {"single_select", "multiple_select"}


def _option_ids(name: str) -> dict:
    """Option value -> id from the LIVE schema (select fields are written by option id)."""
    f = next((x for x in live_schema() if x["name"] == name), None)
    return {o["value"]: o["id"] for o in (f or {}).get("select_options", [])}


def build_payload(fields: dict, option_ids=None) -> dict:
    """Validate against config/baserow-mapping.yaml; select values are given by NAME and sent as option ids."""
    spec = mapping()["fields"]
    option_ids = option_ids or _option_ids
    payload = {}
    for name, value in fields.items():
        if name not in WRITABLE:
            raise ValueError(f"field {name!r} is not writable by Hermes Career Buddy")
        ftype = spec[name]["type"]
        if ftype in SELECT_TYPES:
            values = value if isinstance(value, list) else [value]
            values = [v for v in values if v not in (None, "")]
            bad = [v for v in values if v not in spec[name]["options"]]
            if bad:
                raise ValueError(f"{name} option(s) {bad} do not exist in the mapping")
            if ftype == "single_select" and len(values) > 1:
                raise ValueError(f"{name} takes one value")
            ids = option_ids(name)
            missing = [v for v in values if v not in ids]
            if missing:
                raise ValueError(f"{name} option(s) {missing} missing in live Baserow (run schema-check)")
            payload[name] = ([ids[v] for v in values] if ftype == "multiple_select"
                             else (ids[values[0]] if values else None))
        elif ftype == "date" and value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)):
            raise ValueError(f"{name} must be YYYY-MM-DD")
        else:
            payload[name] = value
    return payload


def _readback_value(row_value):
    """Normalise a read-back value for comparison: select -> option id(s)."""
    if isinstance(row_value, dict) and "id" in row_value:
        return row_value["id"]
    if isinstance(row_value, list) and row_value and isinstance(row_value[0], dict):
        return sorted(o["id"] for o in row_value)
    return row_value


def write(kind: str, fields: dict, idempotency_key: str, row_id: int | None = None, live: bool = False,
          task_id: str = "manual") -> dict:
    """kind: create | update. Returns a preview unless every live gate passes."""
    if kind not in {"create", "update"} or (kind == "update" and not row_id):
        raise ValueError("kind must be create, or update with row_id")
    payload = build_payload(fields)
    preview = {"table_id": mapping()["table_id"], "kind": kind, "row_id": row_id, "payload": payload,
               "idempotency_key": idempotency_key, "write_performed": False}
    done = state.ledger_get(idempotency_key)
    if done and done["status"] == "applied":
        return {**preview, "skipped": "already applied", "result_ref": done["result_ref"]}
    if not live:
        return {**preview, "mode": "dry_run"}
    import sys
    if os.environ.get("HCB_NO_LIVE_WRITES") or "unittest" in sys.modules:
        raise PermissionError("test run: live Baserow writes are disabled (2026-11-19: a test wrote row 31).")
    if not config()["features"]["baserow_live_writes"]:
        raise PermissionError("features.baserow_live_writes is false: live Baserow writes are disabled.")
    tid = mapping()["table_id"]
    state.ledger_put(idempotency_key, f"baserow_{kind}", str(row_id or "pending"), "attempted")
    try:
        if kind == "create":
            created = _request("POST", f"/api/database/rows/table/{tid}/?user_field_names=true", payload)
            row_id = created.get("id")
        else:
            _request("PATCH", f"/api/database/rows/table/{tid}/{int(row_id)}/?user_field_names=true", payload)
    except BaserowError as exc:
        state.error_event("baserow_write", task_id, "adapter", "uncertain_effect", str(exc), 1,
                          "write may or may not be applied", [], "read_before_retry",
                          "Inspect table 839 before any retry")
        raise
    row = get_row(row_id)
    def same(k, v):
        got = _readback_value(row.get(k))
        if isinstance(v, list):
            return sorted(v) == (got if isinstance(got, list) else [got] if got is not None else [])
        if isinstance(v, (int, float)) and got not in (None, ""):
            try:
                return float(got) == float(v)
            except (TypeError, ValueError):
                return False
        return str(got if got is not None else "") == str(v if v is not None else "")
    mismatched = [k for k, v in payload.items() if not same(k, v)]
    verified = not mismatched
    state.ledger_put(idempotency_key, f"baserow_{kind}", str(row_id), "applied" if verified else "unverified")
    state.event("baserow_write", task_id=task_id, write_kind=kind, row_id=row_id, verified=verified,
                fields=sorted(payload))
    return {**preview, "row_id": row_id, "write_performed": True, "verified": verified, "mismatched": mismatched}


# ---------- P-7: Documents (838) and Contacts (837) ----------
def table_spec(name: str) -> dict:
    return mapping()["tables"][name]


def table_fields(name: str) -> list[dict]:
    return _request("GET", f"/api/database/fields/table/{table_spec(name)['table_id']}/")


def table_rows(name: str) -> list[dict]:
    rows, page, tid = [], 1, table_spec(name)["table_id"]
    while True:
        data = _request("GET", f"/api/database/rows/table/{tid}/?user_field_names=true&size=100&page={page}")
        rows.extend(data["results"])
        if not data.get("next"):
            return rows
        page += 1


def table_drift(name: str) -> list[str]:
    spec = table_spec(name)["fields"]
    live = {f["name"]: f for f in table_fields(name)}
    out = []
    for n, s in spec.items():
        f = live.get(n)
        if not f:
            out.append(f"{name}: missing field {n}")
        elif f["type"] != s["type"]:
            out.append(f"{name}.{n}: type {f['type']} != {s['type']}")
        elif "options" in s and [o["value"] for o in f.get("select_options", [])] != s["options"]:
            out.append(f"{name}.{n}: options changed")
    return out


def table_payload(name: str, fields: dict, option_ids=None) -> dict:
    """Validate against the mapping; selects by name -> option id; links as row ids; files as uploaded names."""
    spec = table_spec(name)["fields"]
    if option_ids is None:
        live = {f["name"]: f for f in table_fields(name)}
        option_ids = lambda n: {o["value"]: o["id"] for o in live.get(n, {}).get("select_options", [])}
    out = {}
    for n, v in fields.items():
        if n not in spec:
            raise ValueError(f"{name}: field {n!r} is not writable")
        t = spec[n]["type"]
        if v in (None, ""):
            continue
        if t == "single_select":
            if v not in spec[n]["options"]:
                raise ValueError(f"{name}.{n}: option {v!r} not in mapping")
            ids = option_ids(n)
            if v not in ids:
                raise ValueError(f"{name}.{n}: option {v!r} missing in live Baserow")
            out[n] = ids[v]
        elif t == "link_row":
            out[n] = [int(x) for x in (v if isinstance(v, list) else [v])]
        elif t == "file":
            out[n] = v if isinstance(v, list) else [v]
        elif t == "boolean":
            out[n] = bool(v)
        else:
            out[n] = v
    return out


def upload_file(path) -> dict:
    """Upload a local file to Baserow user files; returns the value a file field takes ({"name": ...})."""
    import mimetypes
    import uuid
    from pathlib import Path as _P
    path = _P(path)
    m = mapping()
    base = m["base_url"]
    if not re.fullmatch(r"http://(localhost|127\.0\.0\.1):\d+", base):
        raise BaserowError("Only a loopback Baserow URL is allowed.")
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n").encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(base + "/api/user-files/upload-file/", data=body, method="POST")
    req.add_header("Authorization", "Token " + _token())
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(req, timeout=60) as resp:
            return {"name": json.loads(resp.read().decode())["name"]}
    except urllib.error.HTTPError as exc:
        raise BaserowError(f"Baserow upload returned HTTP {exc.code}; body withheld.") from None


def write_table(name: str, kind: str, fields: dict, idempotency_key: str, row_id: int | None = None,
                live: bool = False, task_id: str = "manual", option_ids=None) -> dict:
    """Create/update one row in Documents or Contacts with the same gates as Applications (never delete)."""
    import sys
    if kind not in {"create", "update"} or (kind == "update" and not row_id):
        raise ValueError("kind must be create, or update with row_id")
    payload = table_payload(name, fields, option_ids)
    preview = {"table": name, "kind": kind, "row_id": row_id, "payload": payload,
               "idempotency_key": idempotency_key, "write_performed": False}
    done = state.ledger_get(idempotency_key)
    if done and done["status"] == "applied":
        return {**preview, "skipped": "already applied", "result_ref": done["result_ref"]}
    if not live:
        return {**preview, "mode": "dry_run"}
    if os.environ.get("HCB_NO_LIVE_WRITES") or "unittest" in sys.modules:
        raise PermissionError("test run: live Baserow writes are disabled.")
    if not config()["features"]["baserow_live_writes"]:
        raise PermissionError("features.baserow_live_writes is false: live Baserow writes are disabled.")
    tid = table_spec(name)["table_id"]
    state.ledger_put(idempotency_key, f"baserow_{name}_{kind}", str(row_id or "pending"), "attempted")
    try:
        if kind == "create":
            row_id = _request("POST", f"/api/database/rows/table/{tid}/?user_field_names=true", payload).get("id")
        else:
            _request("PATCH", f"/api/database/rows/table/{tid}/{int(row_id)}/?user_field_names=true", payload)
    except BaserowError as exc:
        state.error_event("baserow_write", task_id, "adapter", "uncertain_effect", str(exc), 1,
                          "write may or may not be applied", [], "read_before_retry", f"Inspect table {tid} first")
        raise
    row = _request("GET", f"/api/database/rows/table/{tid}/{int(row_id)}/?user_field_names=true")
    simple = {k: v for k, v in payload.items() if table_spec(name)["fields"][k]["type"] in ("text", "long_text", "url", "number", "boolean")}
    mismatched = [k for k, v in simple.items() if str(row.get(k) if row.get(k) is not None else "") != str(v)]
    verified = not mismatched
    state.ledger_put(idempotency_key, f"baserow_{name}_{kind}", str(row_id), "applied" if verified else "unverified")
    state.event("baserow_write", task_id=task_id, table=name, write_kind=kind, row_id=row_id, verified=verified)
    return {**preview, "row_id": row_id, "write_performed": True, "verified": verified, "mismatched": mismatched}

