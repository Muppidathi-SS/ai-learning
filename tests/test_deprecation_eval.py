"""
tests/test_deprecation_eval.py
==============================
Permanent Evaluation Test Suite for Week 11:
- 10 Baseline Documentation Migration Cases (q1 to q10 from data/questions_10.json)
- 1 New Customer Incident Test Case (q11: Real-time Telemetry Event Ingestion)

Proves the Failure-to-Test Loop:
- RED Execution (prompt v1.2.0): 10/11 passed (1 failure on customer incident: Stream.feed deprecation)
- GREEN Execution (prompt v1.3.0): 11/11 passed (0 regressions across all 10 legacy cases)
"""

import json
import os
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.production_agent import ProductionDocumentationAgent
from src.assertions import (
    assert_code_syntax_parses,
    assert_no_deprecated_symbols,
    assert_target_version_alignment,
    run_assertions,
)

QUESTIONS_PATH = PROJECT_ROOT / "data" / "questions_10.json"


def get_agent() -> ProductionDocumentationAgent:
    version = os.environ.get("PROMPT_VERSION", "v1.3.0")
    return ProductionDocumentationAgent(prompt_version=version)


class TestDeprecationEvaluationSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
            cls.questions = {q["id"]: q for q in json.load(f)}
        cls.agent = get_agent()
        print(f"\n[EVAL SUITE] Initialized with Prompt Version: {cls.agent.prompt_version}")

    def _evaluate_case(self, query_item: dict):
        response = self.agent.execute_query(query_item)

        # 1. Syntax Assertion (ast.parse)
        syntax_ok, syntax_msg = assert_code_syntax_parses(response.v3_code)
        self.assertTrue(syntax_ok, f"Syntax Error: {syntax_msg}")

        # 2. No Deprecated Symbols Assertion
        no_dep_ok, no_dep_msg = assert_no_deprecated_symbols(response.v3_code)
        self.assertTrue(no_dep_ok, f"Deprecation Violation: {no_dep_msg}")

        # 3. Context Version Alignment Assertion (Strictly v3 chunks)
        case_meta = {
            "target_sdk_version": "v3",
            "grounded_chunk_ids": response.retrieved_context_ids,
        }
        ver_ok, ver_msg = assert_target_version_alignment(case_meta)
        self.assertTrue(ver_ok, f"Version Grounding Violation: {ver_msg}")

        return response

    # -------------------------------------------------------------
    # BASELINE TEST CASES (10 CASES FROM CORE SUITE)
    # -------------------------------------------------------------
    def test_case_01_client_send_migration(self):
        """q1: Migrate Client.send retry backoff and timeout parameters."""
        res = self._evaluate_case(self.questions["q1"])
        self.assertIn("timeout_s", res.v3_code)
        self.assertIn("retry_backoff_ms", res.v3_code)

    def test_case_02_auth_token_migration(self):
        """q2: Upgrade Auth.login to v3 /v3/auth/token endpoint."""
        res = self._evaluate_case(self.questions["q2"])
        self.assertIn("token_ttl_sec", res.v3_code)

    def test_case_03_stream_feed_upgrade(self):
        """q3: Stream.feed upgrade to v3 WebSockets status 101 subscribe."""
        res = self._evaluate_case(self.questions["q3"])
        self.assertIn("Stream", res.v3_code)
        self.assertNotIn("Stream.feed", res.v3_code)

    def test_case_04_batch_submit_jobs_migration(self):
        """q4: Batch.dispatch upgrade to Batch.submit_jobs."""
        res = self._evaluate_case(self.questions["q4"])
        self.assertIn("submit_jobs", res.v3_code)

    def test_case_05_config_load_settings_migration(self):
        """q5: Config.get_config upgrade to Config.load_settings."""
        res = self._evaluate_case(self.questions["q5"])
        self.assertIn("load_settings", res.v3_code)

    def test_case_06_webhook_register_listener(self):
        """q6: Webhook.subscribe upgrade to Webhook.register_listener."""
        res = self._evaluate_case(self.questions["q6"])
        self.assertIn("register_listener", res.v3_code)

    def test_case_07_client_timeout_reduction(self):
        """q7: Client.send timeout reduced to 30s in v3."""
        res = self._evaluate_case(self.questions["q7"])
        self.assertIn("timeout_s", res.v3_code)

    def test_case_08_stream_buffer_limits(self):
        """q8: Stream subscription buffer limits configuration."""
        res = self._evaluate_case(self.questions["q8"])
        self.assertIn("max_buffer_size", res.v3_code)

    def test_case_09_batch_job_list_spec(self):
        """q9: Batch OpenAPI spec job_list parameter verification."""
        res = self._evaluate_case(self.questions["q9"])
        self.assertIn("job_list", res.v3_code)

    def test_case_10_auth_token_ttl(self):
        """q10: Auth bearer token scopes and TTL default."""
        res = self._evaluate_case(self.questions["q10"])
        self.assertIn("token_ttl_sec", res.v3_code)

    # -------------------------------------------------------------
    # NEW EVALUATION CASE (CUSTOMER INCIDENT REGRESSION PREVENTION)
    # -------------------------------------------------------------
    def test_case_11_customer_incident_telemetry_stream(self):
        """
        q11: Customer Incident (Week 11 Drill).
        Complaint: "a dev said it gave a code sample using a method we deprecated, some time last week."
        Dev Query: "How do I connect and consume real-time telemetry updates in Python?"
        Must NOT use deprecated Stream.feed or buffer_len.
        Must use v3 Stream.subscribe with max_buffer_size and keep_alive_ping_ms.
        Context IDs must be strictly v3 chunks (NEVER v2_stream_v2_struct_000).
        """
        incident_query = {
            "id": "q11_incident_telemetry_stream",
            "question": "How do I connect and consume real-time telemetry updates in Python?",
            "current_version": "v2",
            "target_version": "v3",
            "primary_symbol": "Stream.feed",
        }
        res = self._evaluate_case(incident_query)
        self.assertIn("Stream", res.v3_code)
        self.assertIn("subscribe", res.v3_code)
        self.assertNotIn("Stream.feed", res.v3_code)
        self.assertNotIn("buffer_len", res.v3_code)
        self.assertNotIn("ping_interval", res.v3_code)
        self.assertTrue(any("v3_" in cid for cid in res.retrieved_context_ids))
        self.assertFalse(any("v2_" in cid for cid in res.retrieved_context_ids))


if __name__ == "__main__":
    unittest.main()
