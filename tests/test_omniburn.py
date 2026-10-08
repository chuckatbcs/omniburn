#!/usr/bin/env python3
"""
Unit and integration tests for OmniBurn.
"""

import os
import unittest
import urllib.request
import json
from engine.db import get_connection, init_db
from engine.calculator import recalculate_all_yields
from engine.recommender import recommend
from engine.telemetry_logger import log_task_run, get_telemetry_summary

class TestOmniBurn(unittest.TestCase):
    def test_database_tables(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        conn.close()

        expected = ["subscriptions", "quota_pools", "models", "task_tiers", "model_task_yields", "model_changelog", "telemetry_runs"]
        for t in expected:
            self.assertIn(t, tables, f"Missing table {t}")

    def test_recommender_dual_routing(self):
        # Tier 2 Quota First
        rec_t2_q = recommend(tier_id=2, strategy="quota_first")
        top_t2_q = rec_t2_q["top_recommendation"]["model_id"]
        self.assertIn("flash", top_t2_q.lower(), "Tier 2 Quota-First should recommend Flash")

        # Tier 3 Time/Reliability First
        rec_t3_t = recommend(tier_id=3, strategy="time_reliability_first")
        top_t3_t = rec_t3_t["top_recommendation"]["model_id"]
        self.assertTrue(
            "pro" in top_t3_t.lower() or "sol" in top_t3_t.lower(),
            f"Tier 3 Time/Reliability should recommend Pro or Sol, got {top_t3_t}"
        )

        # Tier 4 Workload Capability Gating
        rec_t4_q = recommend(tier_id=4, strategy="quota_first")
        top_t4_q = rec_t4_q["top_recommendation"]["model_id"]
        self.assertTrue(
            any(k in top_t4_q.lower() for k in ["opus", "astra", "pro", "sol"]),
            f"Tier 4 should recommend frontier model, got {top_t4_q}"
        )
        self.assertNotIn("flash", top_t4_q.lower(), "Tier 4 must never recommend Flash")
        self.assertNotIn("composer", top_t4_q.lower(), "Tier 4 must never recommend Composer")

    def test_telemetry_summary(self):
        summary = get_telemetry_summary()
        self.assertGreaterEqual(len(summary), 4, "Should have empirical lane summaries")
        for r in summary:
            self.assertIn("first_pass_rate_pct", r)
            self.assertIn("sec_per_completed", r)
            self.assertIn("tokens_per_completed", r)

    def test_api_status(self):
        req = urllib.request.Request("http://localhost:8787/api/status")
        with urllib.request.urlopen(req, timeout=5) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["monthly_spend"], 59.99)
            self.assertGreaterEqual(len(data["quota_pools"]), 5)

    def test_model_and_provider_toggles(self):
        from engine.toggles import toggle_model, toggle_provider
        
        # Test disabling model
        res = toggle_model("gemini-3.8-flash-medium", is_active=False)
        self.assertEqual(res["status"], "ok")
        self.assertFalse(res["is_active"])

        # Recommender refactors
        rec = recommend(tier_id=2, strategy="quota_first")
        self.assertNotEqual(rec["top_recommendation"]["model_id"], "gemini-3.8-flash-medium")

        # Re-enable model
        res_re = toggle_model("gemini-3.8-flash-medium", is_active=True)
        self.assertTrue(res_re["is_active"])
        rec_re = recommend(tier_id=2, strategy="quota_first")
        self.assertEqual(rec_re["top_recommendation"]["model_id"], "gemini-3.8-flash-medium")

        # Test disabling provider
        res_p = toggle_provider("Google", is_active=False)
        self.assertEqual(res_p["status"], "ok")
        self.assertFalse(res_p["is_active"])
        
        # Re-enable provider
        res_pen = toggle_provider("Google", is_active=True)
        self.assertTrue(res_pen["is_active"])

    def test_workload_classifier(self):
        from engine.classifier import classify_workload
        
        # Tier 1 micro
        c1 = classify_workload("fix syntax error typo in utils.py")
        self.assertEqual(c1["tier_id"], 1)
        self.assertEqual(c1["intent"], "micro_syntax")

        # Tier 2 standard
        c2 = classify_workload("write unit tests and implement function helper")
        self.assertEqual(c2["tier_id"], 2)

        # Tier 3 multi-file
        c3 = classify_workload("refactor multi-file database service contract")
        self.assertEqual(c3["tier_id"], 3)

        # Tier 4 repo-scale architecture
        c4 = classify_workload("rearchitect system for a monorepo multi-agent autonomous workflow")
        self.assertEqual(c4["tier_id"], 4)
        self.assertEqual(c4["intent"], "repo_scale_architecture")
        self.assertEqual(c4["recommended_strategy"], "time_reliability_first")

    def test_golden_harness_suite(self):
        from engine.golden_harness import run_golden_suite
        res = run_golden_suite(tier_id=1)
        self.assertTrue(res["first_pass_success"])
        self.assertEqual(res["status"], "passed")
        self.assertGreater(res["tokens_evaluated"], 0)

    def test_model_lifecycle_management(self):
        from engine.sync_engine import add_model, deprecate_model, restore_model, remove_model
        
        test_id = "test-unit-model-x"
        # 1. Add model
        add_res = add_model({
            "model_id": test_id,
            "display_name": "Test Unit Model X",
            "provider": "UnitTest",
            "harness": "Test Harness",
            "pool_id": "other_models",
            "context_window": 128000,
            "input_cost_per_m": 1.5,
            "output_cost_per_m": 6.0
        })
        self.assertEqual(add_res["status"], "ok")
        self.assertEqual(add_res["event_type"], "NEW_MODEL")

        # Verify in DB
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT is_active FROM models WHERE model_id = ?", (test_id,))
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["is_active"], 1)

        # Verify yields generated
        cur.execute("SELECT COUNT(*) as cnt FROM model_task_yields WHERE model_id = ?", (test_id,))
        yield_count = cur.fetchone()["cnt"]
        self.assertEqual(yield_count, 4)

        # 2. Deprecate model
        dep_res = deprecate_model(test_id, reason="Unit test deprecation")
        self.assertEqual(dep_res["status"], "ok")
        self.assertEqual(dep_res["event_type"], "MODEL_DEPRECATED")

        cur.execute("SELECT is_active FROM models WHERE model_id = ?", (test_id,))
        self.assertEqual(cur.fetchone()["is_active"], 0)

        # 3. Restore model
        rest_res = restore_model(test_id)
        self.assertEqual(rest_res["status"], "ok")
        self.assertEqual(rest_res["event_type"], "MODEL_REACTIVATED")

        cur.execute("SELECT is_active FROM models WHERE model_id = ?", (test_id,))
        self.assertEqual(cur.fetchone()["is_active"], 1)

        # 4. Remove model
        rem_res = remove_model(test_id)
        self.assertEqual(rem_res["status"], "ok")
        self.assertEqual(rem_res["event_type"], "MODEL_REMOVED")

        cur.execute("SELECT * FROM models WHERE model_id = ?", (test_id,))
        self.assertIsNone(cur.fetchone())
        cur.execute("SELECT COUNT(*) as cnt FROM model_task_yields WHERE model_id = ?", (test_id,))
        self.assertEqual(cur.fetchone()["cnt"], 0)
        conn.close()

if __name__ == "__main__":
    unittest.main()
