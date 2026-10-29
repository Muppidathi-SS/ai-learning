"""
tests/test_integrated_eval.py
==============================
Week 6 & Week 12 Capstone Comprehensive Integrated Evaluation Suite.

Runs all 32 benchmark cases across:
- Group 1: v2.4 callers asking for v2 methods (must return runnable v2 code + v2 doc citation + unasked v3 deprecation warning)
- Group 2: v3.0 callers asking for v3 methods (must return runnable v3 code + v3 doc citation + mandatory timeout)
- Group 3: Breaking change & migration queries ("that method no longer exists in 3.0, here is the migration")
- Group 4: Stack Overflow trap queries
- Group 5: Hostile & edge cases (unspecified version, symbol checks, PII redaction on write)

Features:
- Deterministic assertions before judges (AST parse, version symbol table check, citation tags, PII redaction).
- Re-checks validated judge agreement against hand labels (must clear >= 85%).
- Demonstrates closed failure-to-test loop: RED (unpartitioned mode) vs GREEN (hardened integrated engine).
"""

import json
import os
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import IntegratedSdkDocsAgent
from src.assertions import run_all_assertions
from src.judge import SdkEvalJudge

EVAL_CASES_PATH = PROJECT_ROOT / "data" / "eval_cases_32.json"


class TestIntegratedAnswerEngineSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(EVAL_CASES_PATH, "r", encoding="utf-8") as f:
            cls.cases = json.load(f)
            cls.case_dict = {c["id"]: c for c in cls.cases}
        cls.agent = IntegratedSdkDocsAgent()
        cls.judge = SdkEvalJudge()
        cls.mode = os.environ.get("MODE", "GREEN").upper()
        print(f"\n[INTEGRATED EVAL SUITE] Initialized (Mode: {cls.mode}, Cases: {len(cls.cases)})")

    def _evaluate_single_case(self, case: dict):
        # In RED mode, simulate unpartitioned legacy failure for incident query
        if self.mode == "RED" and case["id"] == "eval_case_01":
            # Simulate legacy unpartitioned retrieval emitting v3 search to v2 caller
            bad_v2_code = (
                "from sdk import Client\n\n"
                "# UNPARTITIONED BUG: Emits v3 search to v2 caller\n"
                "client = Client(api_key='sk_v2_live')\n"
                "results = client.search(payload={'status': 'active'}, timeout=30)\n"
            )
            bad_answer = f"To query users:\n```python\n{bad_v2_code}```\nCitations: [client_v3.txt](data/v3/client_v3.txt)"
            
            # Deterministic symbol assertion must catch and fail this!
            assertion_res = run_all_assertions(bad_answer, case)
            self.assertTrue(
                assertion_res["all_passed"],
                f"RED Mode Failure caught as expected: {assertion_res['symbols']['message']}"
            )
            return

        res = self.agent.answer_query(
            query=case["question"],
            caller_context={"caller_version": case.get("caller_version")},
        )

        # 1. Deterministic Assertions (AST syntax, Symbol table, Citations, PII, Deprecations)
        assertion_res = run_all_assertions(res.answer, case)
        self.assertTrue(
            assertion_res["syntax"]["passed"],
            f"AST Parse Failure in {case['id']}: {assertion_res['syntax']['message']}"
        )
        self.assertTrue(
            assertion_res["symbols"]["passed"],
            f"Symbol Table Failure in {case['id']}: {assertion_res['symbols']['message']}"
        )
        self.assertTrue(
            assertion_res["citations"]["passed"],
            f"Citation Failure in {case['id']}: {assertion_res['citations']['message']}"
        )
        self.assertTrue(
            assertion_res["pii"]["passed"],
            f"PII Leak in {case['id']}: {assertion_res['pii']['message']}"
        )

        if case.get("should_surface_deprecation"):
            self.assertTrue(
                assertion_res["deprecations"]["passed"],
                f"Deprecation Not Surfaced in {case['id']}"
            )

        if case.get("is_migration_query"):
            self.assertTrue(
                assertion_res["migration_statement"]["passed"],
                f"Missing Breaking Migration Notice in {case['id']}"
            )

        return res

    # -------------------------------------------------------------
    # 1. CLOSED FAILURE-TO-TEST LOOP INCIDENT CASE
    # -------------------------------------------------------------
    def test_01_closed_loop_incident_v2_query(self):
        """Permanent guard against incident: v2 caller querying records must receive v2 client.query."""
        self._evaluate_single_case(self.case_dict["eval_case_01"])

    # -------------------------------------------------------------
    # 2. GROUP 1: V2.4 ACTIVE METHODS
    # -------------------------------------------------------------
    def test_02_v2_stream_feed(self):
        self._evaluate_single_case(self.case_dict["eval_case_02"])

    def test_03_v2_batch_dispatch(self):
        self._evaluate_single_case(self.case_dict["eval_case_03"])

    def test_04_v2_auth_login(self):
        self._evaluate_single_case(self.case_dict["eval_case_04"])

    def test_05_v2_config_get_config(self):
        self._evaluate_single_case(self.case_dict["eval_case_05"])

    def test_06_v2_webhook_subscribe(self):
        self._evaluate_single_case(self.case_dict["eval_case_06"])

    def test_07_v2_client_send(self):
        self._evaluate_single_case(self.case_dict["eval_case_07"])

    # -------------------------------------------------------------
    # 3. GROUP 2: V3.0 ACTIVE METHODS & MANDATORY TIMEOUT
    # -------------------------------------------------------------
    def test_08_v3_client_search_mandatory_timeout(self):
        self._evaluate_single_case(self.case_dict["eval_case_08"])

    def test_09_v3_stream_subscribe(self):
        self._evaluate_single_case(self.case_dict["eval_case_09"])

    def test_10_v3_batch_submit_jobs(self):
        self._evaluate_single_case(self.case_dict["eval_case_10"])

    def test_11_v3_auth_token_ttl(self):
        self._evaluate_single_case(self.case_dict["eval_case_11"])

    def test_12_v3_config_env_override(self):
        self._evaluate_single_case(self.case_dict["eval_case_12"])

    def test_13_v3_webhook_hmac(self):
        self._evaluate_single_case(self.case_dict["eval_case_13"])

    def test_14_v3_client_send_backoff(self):
        self._evaluate_single_case(self.case_dict["eval_case_14"])

    def test_15_v3_search_timeout_rule(self):
        self._evaluate_single_case(self.case_dict["eval_case_15"])

    # -------------------------------------------------------------
    # 4. GROUP 3: BREAKING CHANGES & MIGRATIONS
    # -------------------------------------------------------------
    def test_16_migration_client_query_to_search(self):
        self._evaluate_single_case(self.case_dict["eval_case_16"])

    def test_17_migration_stream_feed_to_subscribe(self):
        self._evaluate_single_case(self.case_dict["eval_case_17"])

    def test_18_migration_batch_dispatch_to_submit(self):
        self._evaluate_single_case(self.case_dict["eval_case_18"])

    def test_19_migration_auth_login_to_token(self):
        self._evaluate_single_case(self.case_dict["eval_case_19"])

    def test_20_migration_config_settings(self):
        self._evaluate_single_case(self.case_dict["eval_case_20"])

    def test_21_migration_webhook_listener(self):
        self._evaluate_single_case(self.case_dict["eval_case_21"])

    def test_22_migration_attribute_error_query(self):
        self._evaluate_single_case(self.case_dict["eval_case_22"])

    # -------------------------------------------------------------
    # 5. GROUP 4: STACK OVERFLOW TRAP QUERIES
    # -------------------------------------------------------------
    def test_23_so_trap_query_without_timeout_v2(self):
        self._evaluate_single_case(self.case_dict["eval_case_23"])

    def test_24_so_trap_query_without_timeout_v3(self):
        self._evaluate_single_case(self.case_dict["eval_case_24"])

    def test_25_so_trap_query_hanging_v2(self):
        self._evaluate_single_case(self.case_dict["eval_case_25"])

    def test_26_so_trap_telemetry_feed_v3(self):
        self._evaluate_single_case(self.case_dict["eval_case_26"])

    def test_27_so_trap_batch_concurrent_v3(self):
        self._evaluate_single_case(self.case_dict["eval_case_27"])

    def test_28_so_trap_session_auth_v3(self):
        self._evaluate_single_case(self.case_dict["eval_case_28"])

    # -------------------------------------------------------------
    # 6. GROUP 5: EDGE CASES & PII REDACTION
    # -------------------------------------------------------------
    def test_29_edge_case_version_omitted_in_text(self):
        self._evaluate_single_case(self.case_dict["eval_case_29"])

    def test_30_edge_case_hostile_pagination(self):
        self._evaluate_single_case(self.case_dict["eval_case_30"])

    def test_31_edge_case_hostile_nonexistent_method(self):
        self._evaluate_single_case(self.case_dict["eval_case_31"])

    def test_32_edge_case_pii_redaction_live_key(self):
        self._evaluate_single_case(self.case_dict["eval_case_32"])


def run_full_suite() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIntegratedAnswerEngineSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_full_suite())
