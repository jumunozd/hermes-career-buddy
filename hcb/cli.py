"""`bin/hcb` command line: the deterministic tools Hermes calls through its terminal tool."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .util import ROOT, config, dump


def _out(obj):
    sys.stdout.write(dump(obj))


def cmd_privacy_scan(a):
    from . import privacy
    hits = privacy.scan()
    summary = {}
    for h in hits:
        summary.setdefault(h["file"], []).append(f'{h["line"]}:{h["kind"]}:{h["value"]}')
    _out({"clean": not hits, "hits": len(hits), "files": len(summary),
          "by_file": summary if a.verbose else {f: len(v) for f, v in summary.items()}})
    if hits:
        raise SystemExit(1)


def cmd_doctor(_a):
    import shutil
    import subprocess
    from . import engine
    checks = {}
    from .util import authority_path, engine_dir, private_dir
    checks["private_zone"] = str(private_dir().relative_to(ROOT)) if private_dir().is_relative_to(ROOT) else str(private_dir())
    checks["engine_dir"] = (engine_dir() / "build").is_dir()
    checks["ah_evaluator"] = authority_path("ah_evaluator").is_dir()
    checks["engine_fingerprint"] = engine.fingerprint()[:16]
    try:
        from . import ah_adapter
        checks["ah_evaluator_import"] = ah_adapter.method_version()
        ah_adapter.engine_inputs()
        checks["ah_engine_pins_match"] = True
    except Exception as exc:  # report, never crash the doctor
        checks["ah_evaluator_import"] = f"FAIL {type(exc).__name__}: {exc}"
    tok = authority_path("baserow_token_file")
    checks["baserow_token_present"] = tok.is_file()  # existence only; never read here
    checks["hermes_cli"] = shutil.which("hermes") is not None
    from . import writer_pack
    checks["writer_pack_fresh"] = writer_pack.check()["fresh"]
    checks["features"] = config()["features"]
    checks["git_root"] = (ROOT / ".git").is_dir()
    checks["project_skills"] = sorted(p.parent.name for p in (ROOT / ".hermes/skills").rglob("SKILL.md"))
    _out(checks)


def cmd_parse(a):
    from . import commands
    res = commands.parse(a.message)
    if res["intent"] == "prepare" and res["by"] == "report_number":
        from . import report
        rep = report.load(a.report) if a.report else report.latest()
        res["resolution"] = commands.resolve_numbers(res["values"], rep) if rep else {"execute": False,
                                                                                         "errors": ["no report delivered yet"]}
    _out(res)


def cmd_classify(a):
    from . import rules
    _out(rules.classify(json.loads(Path(a.file).read_text())))


def cmd_baserow(a):
    from . import baserow
    if a.op == "schema-check":
        drift = baserow.schema_drift()
        _out({"schema_matches_mapping": not drift, "drift": drift})
    elif a.op == "list":
        rows = baserow.list_rows()
        _out({"count": len(rows), "rows": [{"id": r["id"], "Job Title": r.get("Job Title"), "Company": r.get("Company"),
                                             "Status": (r.get("Status") or {}).get("value") if isinstance(r.get("Status"), dict)
                                                       else [o["value"] for o in r.get("Status") or []],
                                             "tags": baserow.decode_tags(r.get("Notes"))[0]} for r in rows]})
    elif a.op == "dedup":
        _out(baserow.find_duplicates(json.loads(a.fields), baserow.list_rows()))
    elif a.op in ("create", "update"):
        _out(baserow.write(a.op, json.loads(a.fields), a.key, row_id=a.row, live=a.live, task_id=a.task or "manual"))
    elif a.op == "contact-add":
        if not a.fields:
            raise SystemExit("contact-add needs --fields '<json>'")
        f = json.loads(a.fields)
        key = "contact-add:" + "|".join(str(f.get(k, "")).lower() for k in ("Name", "Company"))
        dup = [r["id"] for r in baserow.table_rows("contacts")
               if (r.get("Name") or "").lower() == str(f.get("Name", "")).lower()
               and (r.get("Company") or "").lower() == str(f.get("Company", "")).lower()]
        if dup:
            _out({"skipped": "already in Contacts", "row_ids": dup})
        else:
            _out(baserow.write_table("contacts", "create", f, key, live=a.live, task_id="contact-add"))
    elif a.op == "p7-backfill":
        from . import registry
        _out({"mode": "live" if a.live else "preview (nothing written)",
              **registry.write_p7(registry.p7_backfill(), live=a.live)})
    elif a.op == "publish-docs":
        from pathlib import Path as _P
        from . import registry
        if not a.folder:
            raise SystemExit("publish-docs needs --folder <application version folder>")
        v = _P(a.folder).resolve()
        man = json.loads((v / "manifest.json").read_text())
        ref = man.get("opportunity_ref")
        row = next((r for r in baserow.list_rows() if r.get("Opportunity Ref") == ref), None)
        docs = registry.document_rows(v, ref, (row or {}).get("Company") or "", (row or {}).get("id"))
        _out({"mode": "live" if a.live else "preview", **registry.write_p7({"documents": docs}, live=a.live)})
    elif a.op == "register":
        from datetime import date
        from . import registry
        if not a.snapshot:
            raise SystemExit("register needs --snapshot <file>")
        _out(registry.register_snapshot(a.snapshot, date.today().isoformat(), live=a.live))
    elif a.op == "backfill":
        from datetime import date
        from . import registry
        rows = registry.backfill_rows(date.today().isoformat())
        prev = registry.preview(rows)
        if not a.live:
            _out({"mode": "preview (nothing written)", "rows": len(prev),
                  "items": [{"duplicate": p["duplicate"], **p["fields"]} for p in prev]})
        else:
            done = []
            for p in prev:
                if p["duplicate"]:
                    done.append({"ref": p["fields"]["Opportunity Ref"], "skipped": "duplicate"}); continue
                r = baserow.write("create", p["fields"], "backfill-p6:" + p["fields"]["Opportunity Ref"], live=True,
                                  task_id="backfill-p6")
                done.append({"ref": p["fields"]["Opportunity Ref"], "row_id": r.get("row_id"),
                             "verified": r.get("verified"), "mismatched": r.get("mismatched"), "skipped": r.get("skipped")})
            _out({"mode": "live", "results": done})
    elif a.op == "migrate-schema":
        from . import baserow_schema
        _out(baserow_schema.apply() if a.apply else {**baserow_schema.plan(), "tables": baserow_schema.plan_tables(),
                                                      "mode": "preview (nothing changed)"})


def cmd_ah(a):
    from . import ah_adapter as ah
    if a.op == "validate":
        _out(ah.summary(ah.validate_stored(a.path)))
        return
    if a.op == "vacancy-open":
        _out(ah.vacancy_open_verification(a.approval, a.url, a.read_at))
        return
    ad = Path(a.ad).read_text(encoding="utf-8")
    verification = json.loads(a.verification) if a.verification else None
    ctx = ah.make_context(ad, a.state, verification)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.op == "prompt":
        system, user = ah.build_prompt(ctx)
        (out / "ah-system.txt").write_text(system)
        (out / "ah-user.json").write_text(user)
        _out({"evaluation_id": ctx["evaluation_id"], "system_chars": len(system), "user_chars": len(user)})
    elif a.op in ("run", "finalize"):
        if a.op == "run":
            system, user = ah.build_prompt(ctx)
            raw, execution = ah.run_isolated(system, user, out, a.toolsets)
            (out / "ah-raw.json").write_text(raw)
        else:
            ah.build_prompt(ctx)  # loads fact_index into the context for fact-ref validation
            raw, execution = Path(a.raw).read_text(), {"provider": a.provider, "model": a.model, "toolsets": a.toolsets.split(",")}
        assessment = ah.finalize(raw, ctx, execution)
        (out / "assessment.json").write_text(dump(assessment))
        (out / "assessment.md").write_text(ah.evaluator().render_markdown(assessment))
        _out(ah.summary(assessment))


def cmd_engine(a):
    from . import engine
    if a.op == "fingerprint":
        _out({"engine_fingerprint": engine.fingerprint()})
    elif a.op == "new-version":
        folder, label = engine.new_version_dir(a.opportunity, a.preparation)
        _out({"folder": str(folder), "version_label": label})
    elif a.op == "select":
        res = engine.select_evidence(Path(a.folder))
        _out(res)
        sys.exit(0 if res["passed"] and res["engine_unchanged"] else 1)
    elif a.op == "run":
        res = engine.run_pipeline(Path(a.folder), statement=a.statement)
        _out(res)
        sys.exit(0 if res["all_passed"] and res["engine_unchanged"] else 1)
    elif a.op == "publish":
        _out(engine.publish(Path(a.folder), json.loads(a.meta)))


def cmd_task(a):
    from . import envelopes
    if a.op == "make":
        task = envelopes.make_task(a.role, a.action, a.refs, a.cycle, a.scope, round_=a.round)
        _out({"task": task, "delegate_context": envelopes.delegation_context(task, json.loads(a.payload or "{}"))})
    elif a.op == "validate":
        problems = envelopes.validate_result(json.loads(Path(a.task_file).read_text()), json.loads(Path(a.result_file).read_text()))
        _out({"accepted": not problems, "problems": problems})


def cmd_review(a):
    from . import recruiter_gates as rg
    review = json.loads(Path(a.file).read_text())
    _out({"computed": rg.gates(review, a.round), "problems": rg.check_review(review, a.round),
          "next_step": rg.next_step({**rg.gates(review, a.round),
                                     "next_round_useful": review.get("next_round_useful")}, a.round)})


def cmd_report(a):
    from . import report
    snap = json.loads(Path(a.snapshot).read_text())
    _out(report.build(snap, date.fromisoformat(a.date) if a.date else date.today(), a.report_id))


def cmd_report_send(a):
    from . import dashboard, report
    res = report.send(a.report_id)
    dashboard.refresh_quietly()
    _out(res)


def cmd_backup(a):
    from pathlib import Path as _P
    from . import backup
    if a.verify:
        _out(backup.verify(_P(a.verify)))
        return
    res = backup.run(include_baserow=not a.no_baserow)
    from . import dashboard
    dashboard.refresh_quietly()
    _out(res)


def cmd_prepare_request(a):
    from . import prepare_request
    _out(prepare_request.request(a.ref, a.user or ""))


def cmd_approval(a):
    from . import state
    if a.op == "record":
        _out(state.record_approval("user", a.action, a.objects, a.channel, a.scope, a.source))
    else:
        rec = state.find_approval(action=a.action, obj=a.objects[0] if a.objects else None)
        _out({"approved": rec is not None, "record": rec})


def cmd_contacts(a):
    from . import daily
    _out(daily.extract_contacts(Path(a.ad).read_text(encoding="utf-8")))


def cmd_contact(a):
    from . import contacts
    if a.op == "policy":
        _out(contacts.policy(Path(a.ad).read_text(encoding="utf-8"), a.employer or ""))
    elif a.op == "trigger":
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now = datetime.fromisoformat(a.now) if a.now else datetime.now(ZoneInfo(config()["timezone"]))
        snap = json.loads(Path(a.snapshot).read_text())
        _out(contacts.trigger(snap.get("opportunities", []), now))
    elif a.op == "validate":
        problems = contacts.validate(json.loads(Path(a.result).read_text()),
                                     Path(a.ad).read_text(encoding="utf-8"), a.employer or "")
        _out({"ok": not problems, "problems": problems})
        if problems:
            sys.exit(1)
    elif a.op == "lint":
        r = contacts.outreach_lint(Path(a.file).read_text(encoding="utf-8"))
        _out(r)
        if not r["ok"]:
            sys.exit(1)


def cmd_sources(a):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from . import sources
    if a.op == "read":
        r = sources.read(a.id, a.url)
        _out(r)
        if not r.get("ok"):
            sys.exit(1)
        return
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(ZoneInfo(config()["timezone"]))
    _out(sources.due(now))


def cmd_seen(a):
    from . import seen
    ad = Path(a.ad).read_text(encoding="utf-8") if a.ad else ""
    if a.op == "check":
        _out(seen.check(a.url, ad, a.company or "", a.title or "", a.location or "", a.closing or ""))
    else:
        _out(seen.add(a.url, ad, a.destination, a.reason or "", a.company or "", a.title or "",
                      a.location or "", a.baserow_id, a.rule, a.closing or ""))


def cmd_daily(a):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from . import daily
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(ZoneInfo(config()["timezone"]))
    digest = daily.build_digest(json.loads(Path(a.snapshot).read_text()), now, a.since_hours,
                                already_notified=daily.notified_ids())
    digest["saved_to"] = daily.save(digest)
    _out(digest)


def cmd_deliver_email(a):
    from . import delivery
    res = delivery.send_package(a.folder, a.review, a.fit, a.url, a.title, a.company, a.resend, a.dry_run)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("status") in ("sent", "already", "dry_run") else 1


def cmd_mail_test(a):
    from . import mailer
    from .util import now_iso
    res = mailer.send(f"mail_test:{now_iso()}", "Hermes Career Buddy: correo de prueba",
                      "Prueba de envío (P-10). Si lees esto, el sistema puede enviarte los paquetes de postulación "
                      "y el informe del sábado a esta dirección, y solo a esta dirección.\n\nHermes Career Buddy",
                      what="mail_test", require_flag=False, dry_run=a.dry_run)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("status") in ("sent", "dry_run") else 1


def cmd_daily_send(a):
    from . import daily, dashboard
    res = daily.send(a.digest)
    dashboard.refresh_quietly()
    _out(res)


def cmd_daily_delivered(a):
    from . import daily
    _out(daily.mark_delivered(a.digest, a.channel, a.message_ref, a.failed))


def cmd_writer_pack(a):
    from . import writer_pack
    res = writer_pack.check() if a.check else writer_pack.write()
    _out(res)
    if a.check and not res["fresh"]:
        sys.exit(1)


def cmd_dashboard(a):
    from . import dashboard
    res = dashboard.write()
    if a.open:
        import subprocess
        subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", res["file"]], check=False)
    _out({"summary": res["summary"]} if a.summary else res)


def cmd_discover(a):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from . import discovery
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(ZoneInfo(config()["timezone"]))
    _out(discovery.run(now, max_queries=a.max))


def cmd_sweep(a):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from . import sweep
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(ZoneInfo(config()["timezone"]))
    out = sweep.sweep(now)
    from . import dashboard
    dashboard.refresh_quietly()
    _out({k: out[k] for k in ("per_source", "shortlist", "needs_agent", "skipped_sources", "next")})


def cmd_triage(a):
    from . import targets
    _out(targets.triage(a.title, a.location or ""))


def cmd_targets(a):
    from . import targets
    if a.op == "queries":
        q = targets.queries(a.selective)
        _out({"count": len(q), "queries": q})
    elif a.op == "entry-signal":
        if a.indicators:
            _out(targets.entry_signal(json.loads(Path(a.indicators).read_text())))
        else:
            sug = targets.suggest_indicators(a.title, Path(a.ad).read_text(encoding="utf-8"))
            _out({"suggested_indicators": sug, "result_if_confirmed": targets.entry_signal(sug),
                  "note": "Confirm or correct each indicator with a quoted ad line, then rerun with --indicators <file>."})
    else:
        _out(targets.assess(a.title, Path(a.ad).read_text(encoding="utf-8") if a.ad else ""))


def cmd_review_brief(a):
    from . import review_brief
    _out(review_brief.write(Path(a.folder), Path(a.ad), a.round, a.previous, a.previous_review))


def cmd_event(a):
    from . import state
    fields = json.loads(a.fields)
    if a.kind == "error":
        _out(state.error_event(**fields))
    else:
        _out(state.event(a.kind, **fields))


def main(argv=None):
    p = argparse.ArgumentParser(prog="hcb", description="Hermes Career Buddy deterministic tools")
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("doctor").set_defaults(f=cmd_doctor)
    x = s.add_parser("privacy-scan", help="P-5 leak guard: personal data in files git would publish")
    x.add_argument("--verbose", action="store_true"); x.set_defaults(f=cmd_privacy_scan)
    x = s.add_parser("parse"); x.add_argument("message"); x.add_argument("--report"); x.set_defaults(f=cmd_parse)
    x = s.add_parser("classify"); x.add_argument("file"); x.set_defaults(f=cmd_classify)
    x = s.add_parser("baserow"); x.add_argument("op", choices=["schema-check", "list", "dedup", "create", "update", "migrate-schema", "backfill", "register", "p7-backfill", "publish-docs", "contact-add"])
    x.add_argument("--folder", help="publish-docs only: a published version folder (private/applications/.../vN)")
    x.add_argument("--snapshot", help="register only: the run's snapshot JSON")
    x.add_argument("--apply", action="store_true", help="migrate-schema only: apply (interactive, the user types the login)")
    x.add_argument("--fields", default="{}"); x.add_argument("--key", default=""); x.add_argument("--row", type=int)
    x.add_argument("--live", action="store_true"); x.add_argument("--task"); x.set_defaults(f=cmd_baserow)
    x = s.add_parser("ah"); x.add_argument("op", choices=["validate", "prompt", "run", "finalize", "vacancy-open"])
    x.add_argument("--approval"); x.add_argument("--url"); x.add_argument("--read-at")
    x.add_argument("path", nargs="?"); x.add_argument("--ad"); x.add_argument("--state", default="PRELIMINARY")
    x.add_argument("--verification"); x.add_argument("--out", default="state/ah"); x.add_argument("--raw")
    x.add_argument("--toolsets", default="todo"); x.add_argument("--provider", default="hermes-subagent")
    x.add_argument("--model", default="hermes-default"); x.set_defaults(f=cmd_ah)
    x = s.add_parser("engine"); x.add_argument("op", choices=["fingerprint", "new-version", "select", "run", "publish"])
    x.add_argument("--opportunity"); x.add_argument("--preparation"); x.add_argument("--folder")
    x.add_argument("--meta", default="{}"); x.add_argument("--statement", action="store_true"); x.set_defaults(f=cmd_engine)
    x = s.add_parser("task"); x.add_argument("op", choices=["make", "validate"])
    x.add_argument("--role"); x.add_argument("--action"); x.add_argument("--refs", nargs="*", default=[])
    x.add_argument("--cycle", default=""); x.add_argument("--scope", default="prepare_only; sending_blocked")
    x.add_argument("--round", type=int); x.add_argument("--payload"); x.add_argument("--task-file")
    x.add_argument("--result-file"); x.set_defaults(f=cmd_task)
    x = s.add_parser("review"); x.add_argument("file"); x.add_argument("--round", type=int, required=True); x.set_defaults(f=cmd_review)
    x = s.add_parser("report"); x.add_argument("snapshot"); x.add_argument("--date"); x.add_argument("--report-id"); x.set_defaults(f=cmd_report)
    x = s.add_parser("backup", help="encrypted backup of private/ + Baserow (DB + files), verified and pruned")
    x.add_argument("--verify", help="verify an existing archive instead"); x.add_argument("--no-baserow", action="store_true")
    x.set_defaults(f=cmd_backup)
    x = s.add_parser("prepare-request", help="P-10 Prepare Docs button: idempotent request + Baserow Preparing")
    x.add_argument("--ref", required=True); x.add_argument("--user"); x.set_defaults(f=cmd_prepare_request)
    x = s.add_parser("report-send", help="send a built weekly report PDF to Telegram (hermes send, no LLM)")
    x.add_argument("--report-id", required=True); x.set_defaults(f=cmd_report_send)
    x = s.add_parser("approval"); x.add_argument("op", choices=["record", "check"]); x.add_argument("--action", required=True)
    x.add_argument("--objects", nargs="*", default=[]); x.add_argument("--channel", default="cli")
    x.add_argument("--scope", default=""); x.add_argument("--source", default="manual"); x.set_defaults(f=cmd_approval)
    x = s.add_parser("contacts", help="phones/contact names/emails stated in an ad")
    x.add_argument("ad"); x.set_defaults(f=cmd_contacts)
    x = s.add_parser("contact", help="P-2: approach policy, research trigger, contact validation, outreach lint")
    x.add_argument("op", choices=["policy", "trigger", "validate", "lint"])
    x.add_argument("--ad"); x.add_argument("--employer"); x.add_argument("--snapshot"); x.add_argument("--now")
    x.add_argument("--result"); x.add_argument("--file"); x.set_defaults(f=cmd_contact)
    x = s.add_parser("sources", help="enabled page_read sources due in this run (cadence)")
    x.add_argument("op", choices=["due", "read"]); x.add_argument("--now")
    x.add_argument("--id"); x.add_argument("--url"); x.set_defaults(f=cmd_sources)
    x = s.add_parser("seen", help="Seen-Postings Log: check before A-H, add after every decision")
    x.add_argument("op", choices=["check", "add"]); x.add_argument("--url", required=True); x.add_argument("--ad")
    x.add_argument("--company"); x.add_argument("--title"); x.add_argument("--location")
    x.add_argument("--destination", choices=["baserow", "excluded"]); x.add_argument("--reason")
    x.add_argument("--baserow-id"); x.add_argument("--rule"); x.add_argument("--closing", help="YYYY-MM-DD")
    x.set_defaults(f=cmd_seen)
    x = s.add_parser("daily", help="daily digest of new opportunities (D-USR-01)")
    x.add_argument("snapshot"); x.add_argument("--since-hours", type=int); x.add_argument("--now")
    x.set_defaults(f=cmd_daily)
    x = s.add_parser("deliver-email", help="e-mail a published package to the user (P-10; allowlist: only him)")
    x.add_argument("--folder", required=True); x.add_argument("--review"); x.add_argument("--fit")
    x.add_argument("--url"); x.add_argument("--title"); x.add_argument("--company")
    x.add_argument("--resend", action="store_true"); x.add_argument("--dry-run", action="store_true")
    x.set_defaults(f=cmd_deliver_email)
    x = s.add_parser("mail-test", help="send one test e-mail to the user's own mailbox (works before email_delivery is on)")
    x.add_argument("--dry-run", action="store_true"); x.set_defaults(f=cmd_mail_test)
    x = s.add_parser("daily-send", help="send a saved digest to Telegram (hermes send, no LLM) and record the outcome")
    x.add_argument("--digest", required=True); x.set_defaults(f=cmd_daily_send)
    x = s.add_parser("daily-delivered", help="record a digest send: delivered (offers become notified) or --failed")
    x.add_argument("--digest", required=True); x.add_argument("--channel", default="telegram")
    x.add_argument("--message-ref"); x.add_argument("--failed", metavar="ERROR")
    x.set_defaults(f=cmd_daily_delivered)
    x = s.add_parser("writer-pack", help="regenerate (or --check) the Writer facts digest from the Engine")
    x.add_argument("--check", action="store_true"); x.set_defaults(f=cmd_writer_pack)
    x = s.add_parser("targets", help="match a posting against config/job-targets.yaml, or list queries")
    x.add_argument("op", choices=["match", "queries", "entry-signal"]); x.add_argument("--title", default="")
    x.add_argument("--ad"); x.add_argument("--selective", action="store_true")
    x.add_argument("--indicators"); x.set_defaults(f=cmd_targets)
    x = s.add_parser("sweep", help="deterministic listing sweep: read listings, Seen + triage, short list (no LLM)")
    x.add_argument("--now"); x.set_defaults(f=cmd_sweep)
    x = s.add_parser("dashboard", help="status page + read-only pipeline board (P-13), private/reports/dashboard/")
    x.add_argument("--open", action="store_true"); x.add_argument("--summary", action="store_true"); x.set_defaults(f=cmd_dashboard)
    x = s.add_parser("discover", help="search discovery for search_discovery sources (P-12; no LLM, results are data)")
    x.add_argument("--now"); x.add_argument("--max", type=int); x.set_defaults(f=cmd_discover)
    x = s.add_parser("triage", help="listing-card triage: zone + title, read the detail page or not (RT-14)")
    x.add_argument("--title", required=True); x.add_argument("--location", default="")
    x.set_defaults(f=cmd_triage)
    x = s.add_parser("review-brief", help="compact Recruiter input for one version folder")
    x.add_argument("--folder", required=True); x.add_argument("--ad", required=True)
    x.add_argument("--round", type=int, required=True); x.add_argument("--previous")
    x.add_argument("--previous-review"); x.set_defaults(f=cmd_review_brief)
    x = s.add_parser("event", help="append an audit event: security_event | delivery | error | note ...")
    x.add_argument("kind"); x.add_argument("--fields", default="{}"); x.set_defaults(f=cmd_event)
    a = p.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
