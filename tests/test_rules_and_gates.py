"""Unit tests for Master §13.2 (UT-01..UT-18, deterministic parts) and recruiter.md §7.3."""
import copy
import tempfile
import unittest
from datetime import date

from hcb import commands, envelopes, recruiter_gates as rg, rules, state, util


def _isolate_state():
    cfg = copy.deepcopy(util.config())
    tmp = tempfile.mkdtemp(prefix="hcb-test-")
    cfg["paths"]["state"] = tmp
    cfg["paths"]["reports"] = tmp + "/reports"
    util._CONFIG = cfg
    return tmp


def opp(**kw):
    base = {"baserow_id": kw.pop("id", 1), "employer": "Synthetic Co", "title": "Coordinator", "in_zone": True,
            "eligibility_flag": "8579-OK"}
    base.update(kw)
    return base


class ThresholdAndClassification(unittest.TestCase):
    def test_ut01_fit_5001_is_main(self):
        self.assertTrue(rules.above_threshold(50.01))
        self.assertEqual(rules.classify(opp(fit=50.01))["ranking_category"], "principal")

    def test_ut02_fit_50_excluded(self):
        self.assertFalse(rules.above_threshold(50))
        self.assertFalse(rules.above_threshold("50.00"))
        c = rules.classify(opp(fit=50, entry_signal="Strategic Entry", exploratory_justification="Tier 1 bridge"))
        self.assertEqual((c["rule"], c["ranking_category"]), ("C11", "exploratoria"))
        self.assertEqual(rules.classify(opp(fit=50))["destination"], "seen_log:below_threshold")

    def test_ut03_top5_not_padded(self):
        recs = [opp(id=i, fit=f, ranking_category=rules.classify(opp(fit=f))["ranking_category"])
                for i, f in enumerate([72, 55, 50, 49, 30], 1)]
        top = rules.select_top(recs)
        self.assertEqual([r["baserow_id"] for r in top], [1, 2])

    def test_ut04_three_exploratory_separate_one_line(self):
        recs = [opp(id=10 + i, fit=40, ranking_category="exploratoria", employer_tier=1,
                    exploratory_justification=f"Motivo {i}") for i in range(4)]
        recs.append(opp(id=99, fit=40, ranking_category="exploratoria", exploratory_justification="dos\nlineas"))
        recs.append(opp(id=1, fit=80, ranking_category="principal"))
        ex = rules.select_exploratory(recs)
        self.assertEqual(len(ex), 3)
        self.assertNotIn(99, [r["baserow_id"] for r in ex])
        self.assertNotIn(1, [r["baserow_id"] for r in ex])
        nm = rules.number_map(rules.select_top(recs), ex)
        self.assertEqual(sorted(nm), [1, 6, 7, 8])

    def test_ut08_insufficient_data_no_fit(self):
        c = rules.classify(opp(fit=None, insufficient_data=True))
        self.assertEqual((c["rule"], c["ranking_category"]), ("C7", "pendiente_revision"))

    def test_ut09_expired_becomes_cerrada_not_deleted(self):
        r = rules.expire(opp(closing_date="2026-11-01"), date(2026, 11, 13))
        self.assertEqual(r["estado"], "Cerrada")
        self.assertFalse(r["deleted"])

    def test_c2_8579_fail_and_c10_mandatory_gap(self):
        self.assertEqual(rules.classify(opp(fit=90, eligibility_flag="8579-Fail"))["rule"], "C2")
        c = rules.classify(opp(fit=70, mandatory_gap=True))
        self.assertEqual((c["rule"], c["ranking_category"]), ("C10", "fuera_de_ranking"))

    def test_route_c_exploratory_needs_strategic_entry(self):
        self.assertFalse(rules.is_exploratory_eligible(opp(route="C", employer_tier=1, exploratory_justification="x")))

    def test_eoi_never_main(self):
        c = rules.classify(opp(eoi=True, fit=95, employer_tier=1, exploratory_justification="EOI Tier 1"))
        self.assertEqual(c["ranking_category"], "exploratoria")


class LifecycleAndCommands(unittest.TestCase):
    def setUp(self):
        _isolate_state()

    def test_ut10_prepare_authorises_documents_not_sending(self):
        p = commands.parse("Prepara las ofertas 1, 3")
        self.assertEqual(p["authorises"], "prepare_only")
        self.assertIn("send", p["blocks"])
        ok, why = rules.can_transition("lista_para_envio", "enviada", {"prepare"})
        self.assertFalse(ok)
        ok, _ = rules.can_transition("documentos_aprobados", "lista_para_envio", {"prepare"})
        self.assertFalse(ok)

    def test_not_fit_to_send_blocks_ready(self):
        ok, why = rules.can_transition("documentos_aprobados", "lista_para_envio", {"approve_documents"},
                                       {"send_readiness": "not_fit_to_send"})
        self.assertFalse(ok)
        self.assertIn("D-RC-01", why)

    def test_ut15_followup_recommended_not_sent(self):
        due = rules.followups_due([{"baserow_id": 5, "state": "enviada", "sent_date": "2026-11-01"}], date(2026, 11, 13))
        self.assertEqual(due[0]["action"], "recommend_followup")
        self.assertFalse(due[0]["contact_performed"])
        self.assertEqual(rules.followups_due([{"baserow_id": 5, "state": "enviada", "sent_date": "2026-11-05"}],
                                             date(2026, 11, 13)), [])

    def test_ut16_no_selection_no_assumed_approval(self):
        self.assertIsNone(state.find_approval(action="prepare", obj="5"))
        with self.assertRaises(PermissionError):
            state.require_approval("prepare", "5")

    def test_approval_does_not_extend_by_similarity(self):
        state.record_approval("user", "prepare", [5], "cli", "prepare_only; sending_blocked", "msg-1")
        self.assertIsNotNone(state.require_approval("prepare", "5"))
        with self.assertRaises(PermissionError):
            state.require_approval("send_application", "5")
        with self.assertRaises(PermissionError):
            state.require_approval("prepare", "6")

    def test_command_vocabulary(self):
        self.assertEqual(commands.parse("prepara las ofertas id 812")["by"], "baserow_id")
        self.assertEqual(commands.parse("Cambios 12: más corto el resumen, dame opciones")["variants"], True)
        self.assertEqual(commands.parse("ELIJO b 12")["variant"], "B")
        self.assertEqual(commands.parse("Aprobado 12")["authorises"], "nothing_external")
        self.assertEqual(commands.parse("Enviada 12 2026-11-16")["date"], "2026-11-16")
        self.assertEqual(commands.parse("Resultado 12: rechazo sin feedback")["outcome"], "rechazo")
        self.assertEqual(commands.parse("Follow-up 12 sí")["decision"], True)
        self.assertEqual(commands.parse("aprueba propuesta p3")["proposal_id"], "P-3")
        self.assertEqual(commands.parse("Estado")["intent"], "status")
        self.assertEqual(commands.parse("Envía la postulación a TasWater")["intent"], "refused")
        self.assertEqual(commands.parse("me llamaron de TasWater")["intent"], "unknown")

    def test_numbers_resolve_against_one_report(self):
        rep = {"report_id": "R-2026-W46", "number_map": {"1": 101, "2": 102, "6": 201}}
        r = commands.resolve_numbers([1, 6], rep)
        self.assertTrue(r["execute"])
        self.assertEqual([x["baserow_id"] for x in r["resolved"]], [101, 201])
        self.assertFalse(commands.resolve_numbers([4], rep)["execute"])


class RecruiterGates(unittest.TestCase):
    def review(self, **over):
        base = {"claims": [{"claim_id": "C1", "claim_status": "supported"}],
                "requirements_assessment": [{"requirement_id": "R1", "category": "essential", "evidence_status": "met"},
                                            {"requirement_id": "R2", "category": "legal_gate", "evidence_status": "met"}],
                "document_compliance": [{"document_type": "cv", "present": True, "format_ok": True, "limits": {"ok": True}}],
                "quality_assessment": [], "eligibility_flag": "8579-OK",
                "principal_reasons": [{"reason": "Cumple los esenciales con evidencia", "refs": ["R1"]}],
                "feedback": []}
        base.update(over)
        return base

    def test_pass_when_all_gates(self):
        g = rg.gates(self.review(), 1)
        self.assertEqual(g["verdict"], "Pasa a entrevista")

    def test_integrity_defect_blocks_and_not_fit_to_send(self):
        g = rg.gates(self.review(claims=[{"claim_id": "C1", "claim_status": "overstated"}]), 3)
        self.assertEqual(g["verdict"], "No pasa a entrevista")
        self.assertEqual(g["send_readiness"], "not_fit_to_send")

    def test_ut14_round3_never_waives_legal_gate(self):
        r = self.review(requirements_assessment=[{"requirement_id": "R2", "category": "legal_gate",
                                                  "evidence_status": "absent", "potential_acceptance": "learns fast"}])
        self.assertEqual(rg.gates(r, 3)["gates"]["G3_legal"], "fail")

    def test_round3_accepts_one_essential_by_potential_only(self):
        reqs = [{"requirement_id": "R1", "category": "essential", "evidence_status": "partial", "potential_acceptance": "trainee role"}]
        self.assertEqual(rg.gates(self.review(requirements_assessment=reqs), 1)["verdict"], "No pasa a entrevista")
        self.assertEqual(rg.gates(self.review(requirements_assessment=reqs), 3)["verdict"], "Pasa a entrevista")
        two = reqs + [dict(reqs[0], requirement_id="R3")]
        self.assertEqual(rg.gates(self.review(requirements_assessment=two), 3)["verdict"], "No pasa a entrevista")

    def test_ut11_unrequested_document_fails_g2(self):
        docs = [{"document_type": "cv", "present": True}, {"document_type": "cover_letter", "present": True,
                                                            "unrequested_document": True}]
        self.assertEqual(rg.gates(self.review(document_compliance=docs), 1)["gates"]["G2_documents"], "fail")

    def test_ut13_stop_after_three_rounds(self):
        neg = {"verdict": "No pasa a entrevista"}
        self.assertEqual(rg.next_step(neg, 1), "revise")
        self.assertEqual(rg.next_step(neg, 3), "deliver_with_reasons")

    def test_probability_language_rejected(self):
        r = self.review(verdict="Pasa a entrevista",
                        principal_reasons=[{"reason": "Tiene un 80% de probabilidad", "refs": []}])
        self.assertTrue(any("probabilit" in p for p in rg.check_review(r, 1)))


class Envelopes(unittest.TestCase):
    def setUp(self):
        _isolate_state()

    def test_idempotency_key_is_stable_and_role_bound(self):
        a = envelopes.make_task("writer", "draft", ["812"], "R-2026-W46", "prepare_only")
        b = envelopes.make_task("writer", "draft", ["812"], "R-2026-W46", "prepare_only")
        self.assertEqual(a["idempotency_key"], b["idempotency_key"])
        with self.assertRaises(ValueError):
            envelopes.make_task("writer", "review", ["812"], "x", "prepare_only")

    def test_result_validation(self):
        t = envelopes.make_task("recruiter", "review", ["812"], "v1", "prepare_only", round_=1)
        good = {"task_id": t["task_id"], "idempotency_key": t["idempotency_key"], "role": "recruiter",
                "status": "success", "outputs": {k: [] for k in envelopes.REQUIRED_OUTPUTS["review"]},
                "evidence": [], "missing_data": [], "issues": [], "records_changed": [], "errors": [],
                "instructions_version": "1.0.0"}
        self.assertEqual(envelopes.validate_result(t, good), [])
        bad = dict(good, outputs={"verdict": "x", "application_submitted": True})
        probs = envelopes.validate_result(t, bad)
        self.assertTrue(any("outputs missing" in p for p in probs))
        self.assertTrue(any("out-of-role" in p for p in probs))


if __name__ == "__main__":
    unittest.main()


class AlignmentRanking(unittest.TestCase):
    """P-4 option B (AP-8b0ed42a08712e3b6d21afc1)."""
    def rec(self, i, group, match="contained", hint="principal_candidate", entry=None, bridges=1, closing=None):
        return {"baserow_id": i, "in_zone": True, "eligibility_flag": "8579-OK", "fit": None,
                "target_match": {"group": group, "match": match, "category_hint": hint},
                "entry_signal": entry, "bridges_to": ["x"] * bridges, "closing_date": closing}

    def test_classification_without_ah(self):
        self.assertTrue(rules.alignment_basis())
        self.assertEqual(rules.classify(self.rec(1, "C"))["ranking_category"], "principal")
        self.assertEqual(rules.classify(self.rec(2, None, "none", "out_of_catalogue"))["destination"],
                         "seen_log:out_of_catalogue")
        self.assertEqual(rules.classify(self.rec(3, "E", hint="exploratoria"))["ranking_category"], "exploratoria")
        d = self.rec(4, "D", hint="exploratoria_if_strategic_entry")
        self.assertEqual(rules.classify(d)["destination"], "seen_log:generic_admin_without_strategic_entry")
        d["entry_signal"] = "Strategic Entry"
        self.assertEqual(rules.classify(d)["ranking_category"], "exploratoria")
        self.assertEqual(rules.classify(self.rec(5, None, "none", "needs_review"))["ranking_category"], "pendiente_revision")
        out = self.rec(6, "B"); out["in_zone"] = False
        self.assertEqual(rules.classify(out)["rule"], "C1")       # zone and legal gates still first

    def test_top5_order_and_never_padded(self):
        recs = [self.rec(1, "C"), self.rec(2, "A", "exact"), self.rec(3, "A"), self.rec(4, "B", entry="Strategic Entry"),
                self.rec(5, "B")]
        for r in recs:
            r["ranking_category"] = rules.classify(r)["ranking_category"]
        self.assertEqual([r["baserow_id"] for r in rules.select_top(recs)], [2, 3, 4, 5, 1])
        self.assertEqual(len(rules.select_top(recs[:2])), 2)


class VacancyOpen(unittest.TestCase):
    def test_needs_a_user_approval(self):
        from hcb import ah_adapter
        with self.assertRaises(ValueError):
            ah_adapter.vacancy_open_verification("AP-doesnotexist", "https://x")


class PrepareFromSavedAd(unittest.TestCase):
    """2026-11-17: an ad the user pasted (SEEK) can be prepared by its saved file."""
    def test_saved_ad_file(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        from hcb import commands
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "ads").mkdir()
            (Path(tmp) / "ads" / "seek-acme-analyst.txt").write_text("ad")
            with mock.patch("hcb.util.project_path", side_effect=lambda k: Path(tmp)):
                ok = commands.parse("Prepara la oferta de Acme, Analyst. El aviso está en private/state/ads/seek-acme-analyst.txt")
                missing = commands.parse("Prepara la oferta private/state/ads/nope.txt")
        self.assertEqual((ok["intent"], ok["by"]), ("prepare", "ad_file"))
        self.assertTrue(ok["values"][0].endswith("seek-acme-analyst.txt"))
        self.assertEqual(missing["intent"], "error")
        self.assertEqual(commands.parse("Prepara las ofertas 1 y 3")["by"], "report_number")
