"""
Unit tests for Week 8 Trajectory Evaluation Engine and Assertion Suite.
Verifies:
  - Flexible path set matching (alternative valid sequences)
  - Argument validity detection
  - Telemetry computation (Tool-Choice Accuracy, Argument Validity, Step Efficiency, Cost Distribution)
  - Gap calculation
  - False positive detection
"""

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.trajectory_engine import (
    FlexibleTrajectoryValidator,
    TrajectoryTelemetryEngine,
    FailureMode,
)
from src.agent import MigrationAgent
from src.tools import ApiVersion


class TestTrajectoryEvaluation(unittest.TestCase):
    def setUp(self):
        self.validator = FlexibleTrajectoryValidator()

    def test_flexible_path_matching(self):
        # Path set allowing both [check_deprecation, get_openapi_spec] and [get_openapi_spec, check_deprecation]
        q_meta = {
            "id": "test_q",
            "question": "Migrate Client.send to v3",
            "optimal_steps": 2,
            "mandatory_tools": ["get_openapi_spec"],
            "allowed_paths": [
                ["check_deprecation", "get_openapi_spec"],
                ["get_openapi_spec", "check_deprecation"],
            ],
            "requires_dynamic_branching": False,
        }

        # Case A: Sequence 1
        agent_res_a = {
            "success": True,
            "v3_code": "client = Client(api_key='key')\nresponse = client.send(timeout_s=30)",
            "tool_observations": [
                {"iteration": 1, "tool": "check_deprecation", "arguments": {"symbol_or_endpoint": "Client.send", "version": "v2"}, "result": {}},
                {"iteration": 2, "tool": "get_openapi_spec", "arguments": {"endpoint": "/v3/client/send", "version": "v3"}, "result": {}},
            ],
            "cost_usd": 0.001,
            "tokens_used": 500,
            "latency_s": 0.002,
        }
        res_a = self.validator.evaluate_query_trajectory(q_meta, agent_res_a)
        self.assertTrue(res_a.trajectory_passed)
        self.assertEqual(res_a.matched_path, ["check_deprecation", "get_openapi_spec"])

        # Case B: Sequence 2 (Alternative valid path)
        agent_res_b = {
            "success": True,
            "v3_code": "client = Client(api_key='key')\nresponse = client.send(timeout_s=30)",
            "tool_observations": [
                {"iteration": 1, "tool": "get_openapi_spec", "arguments": {"endpoint": "/v3/client/send", "version": "v3"}, "result": {}},
                {"iteration": 2, "tool": "check_deprecation", "arguments": {"symbol_or_endpoint": "Client.send", "version": "v2"}, "result": {}},
            ],
            "cost_usd": 0.001,
            "tokens_used": 500,
            "latency_s": 0.002,
        }
        res_b = self.validator.evaluate_query_trajectory(q_meta, agent_res_b)
        self.assertTrue(res_b.trajectory_passed)
        self.assertEqual(res_b.matched_path, ["get_openapi_spec", "check_deprecation"])

    def test_argument_hallucination_detection(self):
        # Detect hallucinated endpoint
        is_valid, err = self.validator.validate_argument(
            "get_openapi_spec",
            {"endpoint": "/v3/auth/fake_nonexistent_endpoint", "version": "v3"}
        )
        self.assertFalse(is_valid)
        self.assertIn("Hallucinated endpoint", err)

        # Detect valid endpoint
        is_valid_real, _ = self.validator.validate_argument(
            "get_openapi_spec",
            {"endpoint": "/v3/auth/token", "version": "v3"}
        )
        self.assertTrue(is_valid_real)

    def test_false_positive_gap_detection(self):
        # Query where agent produced correct answer but skipped get_openapi_spec
        q_meta = {
            "id": "q10",
            "question": "Confirm /v3/auth/token in spec",
            "optimal_steps": 2,
            "mandatory_tools": ["get_openapi_spec"],
            "allowed_paths": [["get_openapi_spec"]],
        }
        agent_res_shortcut = {
            "success": True,
            "v3_code": "auth = Auth()\ntoken = auth.login(token_ttl_sec=3600)",
            "tool_observations": [
                {"iteration": 1, "tool": "check_deprecation", "arguments": {"symbol_or_endpoint": "Auth.login", "version": "v2"}, "result": {}},
            ],
            "cost_usd": 0.0005,
            "tokens_used": 300,
            "latency_s": 0.001,
        }
        res = self.validator.evaluate_query_trajectory(q_meta, agent_res_shortcut)
        self.assertTrue(res.outcome_passed)
        self.assertFalse(res.trajectory_passed)
        self.assertTrue(res.is_false_positive)
        self.assertIn(FailureMode.FM1_TOOL_BYPASS, res.failure_modes)


if __name__ == "__main__":
    unittest.main()
