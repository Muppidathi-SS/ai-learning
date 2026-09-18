"""
tests/test_judge.py
===================
Tests judge_v1 baseline vs. judge_v2 few-shot iterated performance.
Compatible with standard python -m unittest and pytest.
"""

import unittest
from src.judge import judge_v1, judge_v2

class TestJudge(unittest.TestCase):
    def test_judge_v1_approves_v2_confusion_blind_spot(self):
        """Judge v1 mistakenly approves v2 timeout default because it looks clear and technical."""
        case = {
            "query": "What is the default timeout_s in Client.send()?",
            "answer": "The default `timeout_s` is `60` seconds for server responses [chunk_id: v2_client_v2_struct_002].",
            "mode": "legacy_version_confusion"
        }
        j_val, reason = judge_v1(case)
        self.assertEqual(j_val, 1)

    def test_judge_v2_penalizes_v2_confusion(self):
        """Judge v2 catches the v2 obsolescence through Few-Shot Example 1."""
        case = {
            "query": "What is the default timeout_s in Client.send()?",
            "answer": "The default `timeout_s` is `60` seconds for server responses [chunk_id: v2_client_v2_struct_002].",
            "mode": "legacy_version_confusion"
        }
        j_val, reason = judge_v2(case)
        self.assertEqual(j_val, 0)
        self.assertIn("Version Correctness", reason)

    def test_judge_v1_approves_missing_code(self):
        """Judge v1 mistakenly approves descriptive prose when code was requested."""
        case = {
            "query": "can you show python code to register a webhook listener?",
            "answer": "`Webhook.register_listener()` requires the cryptographic signature algorithm 'HMAC-SHA256'.",
            "mode": "dry_parameter_omits_code"
        }
        j_val, reason = judge_v1(case)
        self.assertEqual(j_val, 1)

    def test_judge_v2_penalizes_missing_code(self):
        """Judge v2 catches missing code blocks through Few-Shot Example 2."""
        case = {
            "query": "can you show python code to register a webhook listener?",
            "answer": "`Webhook.register_listener()` requires the cryptographic signature algorithm 'HMAC-SHA256'.",
            "mode": "dry_parameter_omits_code"
        }
        j_val, reason = judge_v2(case)
        self.assertEqual(j_val, 0)
        self.assertIn("Format Fidelity", reason)

    def test_judge_v2_approves_correct_v3_answer(self):
        case = {
            "query": "What is token_ttl_sec in v3 Auth.login()?",
            "answer": "The default `token_ttl_sec` parameter for `Auth.login()` is `3600` seconds.",
            "mode": "correct_v3_answer"
        }
        j_val, reason = judge_v2(case)
        self.assertEqual(j_val, 1)
        self.assertIn("Passes all criteria", reason)

if __name__ == "__main__":
    unittest.main()
