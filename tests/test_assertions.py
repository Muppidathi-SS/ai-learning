"""
tests/test_assertions.py
========================
Tests the 3 deterministic assertions moved out of the judge prompt.
Compatible with standard python -m unittest and pytest.
"""

import unittest
from src.assertions import (
    assert_code_syntax_parses,
    assert_no_deprecated_symbols,
    assert_target_version_alignment,
    run_assertions
)

class TestAssertions(unittest.TestCase):
    def test_syntax_assertion_valid_code(self):
        answer = "Here is the code:\n```python\nx = 10\nprint(x)\n```"
        passed, msg = assert_code_syntax_parses(answer)
        self.assertTrue(passed)

    def test_syntax_assertion_invalid_code(self):
        answer = "Broken snippet:\n```python\ndef broken(:\n    pass\n```"
        passed, msg = assert_code_syntax_parses(answer)
        self.assertFalse(passed)
        self.assertIn("SyntaxError", msg)

    def test_syntax_assertion_no_code(self):
        answer = "The default timeout is 30 seconds."
        passed, msg = assert_code_syntax_parses(answer)
        self.assertTrue(passed)

    def test_deprecation_assertion_clean(self):
        answer = "Client.send() uses api_key='sk_live_v3_998877'"
        passed, msg = assert_no_deprecated_symbols(answer)
        self.assertTrue(passed)

    def test_deprecation_assertion_detects_legacy_token(self):
        answer = "client = Client(api_key='sk_v1_legacy_old')"
        passed, msg = assert_no_deprecated_symbols(answer)
        self.assertFalse(passed)
        self.assertIn("deprecated token", msg)

    def test_version_alignment_assertion_v3_ok(self):
        case = {"target_sdk_version": "v3", "grounded_chunk_id": "v3_client_v3_struct_002"}
        passed, msg = assert_target_version_alignment(case)
        self.assertTrue(passed)

    def test_version_alignment_assertion_rejects_v2_chunk(self):
        case = {"target_sdk_version": "v3", "grounded_chunk_id": "v2_client_v2_struct_002"}
        passed, msg = assert_target_version_alignment(case)
        self.assertFalse(passed)
        self.assertIn("legacy", msg)

    def test_run_assertions_aggregate(self):
        clean_case = {
            "answer": "```python\nx = 1\n```\nAPI key is sk_live_v3_123",
            "target_sdk_version": "v3",
            "grounded_chunk_id": "v3_auth_v3_struct_002"
        }
        res = run_assertions(clean_case)
        self.assertTrue(res["all_passed"])

if __name__ == "__main__":
    unittest.main()
