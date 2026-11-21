"""Baserow schema v2 (P-6): plan and apply the additive migration of table 839.

`plan()` reads the live schema with the normal database token (rows-only token: it cannot change fields).
`apply()` is interactive only: the USER runs it in a terminal and types the Baserow e-mail and password
there (getpass). The short-lived login token is kept in memory, never printed, logged or saved. Additive
only: missing fields are created and missing Status options appended; nothing is renamed or deleted.
"""
from __future__ import annotations

import getpass
import json
import re
import sys
import urllib.request

from . import baserow
from .util import mapping

_COLORS = ["light-blue", "light-green", "light-orange", "light-red", "light-gray", "light-cyan", "blue", "green"]


def _field_body(spec: dict) -> dict:
    t = spec["type"]
    body = {"name": spec["name"], "type": t}
    if t == "single_select":
        body["select_options"] = [{"value": v, "color": _COLORS[i % len(_COLORS)]} for i, v in enumerate(spec["options"])]
    elif t == "number":
        body["number_decimal_places"] = int(spec.get("decimals", 0))
    elif t == "date":
        body.update({"date_format": "ISO", "date_include_time": False})
    elif t == "link_row":
        body.update({"link_row_table_id": int(spec["table"]), "has_related_field": False})
    return body


def plan(live: list[dict] | None = None) -> dict:
    v2 = mapping()["schema_v2"]
    live = live if live is not None else baserow.live_schema()
    by_name = {f["name"]: f for f in live}
    create, conflicts = [], []
    for spec in v2["add_fields"]:
        f = by_name.get(spec["name"])
        if not f:
            create.append(_field_body(spec))
        elif f["type"] != spec["type"]:
            conflicts.append(f"{spec['name']}: exists as {f['type']}, expected {spec['type']} (left untouched)")
    status = by_name.get("Status") or {}
    have = [o["value"] for o in status.get("select_options", [])]
    add_opts = [o for o in v2["add_status_options"] if o not in have]
    return {"table_id": mapping()["table_id"], "create_fields": create, "status_field_id": status.get("id"),
            "add_status_options": add_opts, "conflicts": conflicts,
            "nothing_to_do": not create and not add_opts}


def plan_tables(live_by_table: dict | None = None) -> list[dict]:
    """P-7 tables (Documents, Contacts): fields in config `tables.<name>.fields` that are missing, and
    select options that are missing on existing select fields. Additive only."""
    out = []
    for name, spec in (mapping().get("tables") or {}).items():
        live = (live_by_table or {}).get(name)
        if live is None:
            live = baserow.table_fields(name)
        by_name = {f["name"]: f for f in live}
        create, add_opts, conflicts = [], [], []
        for fname, fs in spec["fields"].items():
            f = by_name.get(fname)
            if not f:
                if fs["type"] in ("created_on",):
                    continue
                create.append(_field_body({"name": fname, **fs}))
            elif f["type"] != fs["type"]:
                conflicts.append(f"{name}.{fname}: exists as {f['type']}, expected {fs['type']} (left untouched)")
            elif fs["type"] == "single_select":
                have = [o["value"] for o in f.get("select_options", [])]
                missing = [o for o in fs["options"] if o not in have]
                if missing:
                    add_opts.append({"field_id": f["id"], "field": fname, "existing": f.get("select_options", []),
                                     "add": missing})
        out.append({"table": name, "table_id": spec["table_id"], "create_fields": create,
                    "add_options": add_opts, "conflicts": conflicts,
                    "nothing_to_do": not create and not add_opts})
    return out


def _jwt_request(method: str, path: str, jwt: str | None, body: dict | None = None) -> dict:
    base = mapping()["base_url"]
    if not re.fullmatch(r"http://(localhost|127\.0\.0\.1):\d+", base):
        raise baserow.BaserowError("Only a loopback Baserow URL is allowed.")
    tids = {mapping()["table_id"], *(t["table_id"] for t in (mapping().get("tables") or {}).values())}
    allowed = path == "/api/user/token-auth/" or any(path.startswith(f"/api/database/fields/table/{t}/") for t in tids) \
        or re.fullmatch(r"/api/database/fields/\d+/", path)
    if not allowed:
        raise baserow.BaserowError("Path outside the table-839 schema refused.")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    if jwt:
        req.add_header("Authorization", "JWT " + jwt)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), baserow._NoRedirect())
    try:
        with opener.open(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise baserow.BaserowError(f"Baserow returned HTTP {exc.code}; body withheld.") from None


def apply(stdin=sys.stdin, ask=input, ask_secret=getpass.getpass, request=_jwt_request) -> dict:
    if not stdin.isatty():
        raise PermissionError("migrate-schema --apply is interactive: the user runs it in a terminal and types the login.")
    p = plan()
    pt = plan_tables()
    if p["nothing_to_do"] and all(t["nothing_to_do"] for t in pt):
        return {**p, "tables": pt, "applied": [], "note": "schema already complete"}
    n_extra = sum(len(t["create_fields"]) for t in pt)
    print(f"Se van a crear {len(p['create_fields']) + n_extra} columnas y completar opciones en las tablas "
          f"Applications, Documents y Contacts. Nada se borra ni se renombra.")
    email = ask("Email de Baserow: ").strip()
    password = ask_secret("Contraseña de Baserow (no se muestra): ")
    auth = request("POST", "/api/user/token-auth/", None, {"email": email, "password": password})
    del password
    jwt = auth.get("access_token") or auth.get("token")
    if not jwt:
        raise baserow.BaserowError("Login failed (no token returned).")
    done = []
    for body in p["create_fields"]:
        request("POST", f"/api/database/fields/table/{p['table_id']}/", jwt, body)
        done.append(f"field {body['name']}")
    if p["add_status_options"] and p["status_field_id"]:
        live = {f["name"]: f for f in baserow.live_schema()}
        opts = [{"id": o["id"], "value": o["value"], "color": o["color"]} for o in live["Status"]["select_options"]]
        opts += [{"value": v, "color": "light-gray"} for v in p["add_status_options"]]
        request("PATCH", f"/api/database/fields/{p['status_field_id']}/", jwt, {"select_options": opts})
        done += [f"Status option {v}" for v in p["add_status_options"]]
    for t in pt:
        for body in t["create_fields"]:
            request("POST", f"/api/database/fields/table/{t['table_id']}/", jwt, body)
            done.append(f"{t['table']}: field {body['name']}")
        for o in t["add_options"]:
            opts = [{"id": x["id"], "value": x["value"], "color": x["color"]} for x in o["existing"]]
            opts += [{"value": v, "color": "light-gray"} for v in o["add"]]
            request("PATCH", f"/api/database/fields/{o['field_id']}/", jwt, {"select_options": opts})
            done += [f"{t['table']}.{o['field']} option {v}" for v in o["add"]]
    jwt = None
    return {**p, "tables": pt, "applied": done, "next": "Claude Code: update config/baserow-mapping.yaml fields and run bin/hcb baserow schema-check"}
