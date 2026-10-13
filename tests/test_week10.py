"""
Automated Test Suite for Week 10 Engineering Challenge:
- Arm A: SingleMigrationAgent correctness & output format
- Arm B: OrchestratorSquad execution & delegation hops
- Telemetry & Bottleneck metrics calculation
- Injected Failure (HTTP 500) handling & graceful degradation
- A2A Task State Machine lifecycle transitions
"""

import json
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.single_agent import SingleMigrationAgent
from src.multi_agent.workers import VersionDeprecationWorker, CodeSampleWorker
from src.multi_agent.orchestrator import OrchestratorSquad, HANDOFFS_LOG_PATH
from src.multi_agent.a2a_protocol import A2ATaskStateMachine, A2ATaskState, ORCHESTRATOR_AGENT_CARD


class TestWeek10EngineeringChallenge(unittest.TestCase):

    def test_single_agent_execution(self):
        agent = SingleMigrationAgent()
        query = {
            "id": "q1",
            "question": "Migrate Client.send to v3: Check if timeout_ms is deprecated in favor of timeout_s.",
            "current_version": "v2",
            "target_version": "v3",
        }
        result = agent.run(query)
        self.assertTrue(result.success)
        self.assertIn("timeout_s", result.v3_code)
        self.assertGreater(result.total_tokens, 0)
        self.assertGreaterEqual(result.latency_s, 0.0)

    def test_specialist_workers_independent_execution(self):
        w1 = VersionDeprecationWorker()
        res1 = w1.execute_task("Migrate Stream.feed to v3", "Stream.feed", "v2")
        self.assertEqual(res1["status_code"], 200)
        self.assertTrue(res1["data"]["is_deprecated"])
        self.assertGreater(res1["total_tokens"], 0)

        w2 = CodeSampleWorker()
        res2 = w2.execute_task(
            "Migrate Stream.feed to v3",
            "/v3/stream/subscribe",
            "v3",
            res1["data"],
        )
        self.assertEqual(res2["status_code"], 200)
        self.assertIn("Stream", res2["data"]["v3_code"])
        self.assertGreater(res2["total_tokens"], 0)

    def test_orchestrator_squad_delegation_and_logging(self):
        squad = OrchestratorSquad()
        query = {
            "id": "test_q",
            "question": "Migrate Auth.login to v3: Use token_ttl_sec.",
            "current_version": "v2",
            "target_version": "v3",
        }
        result = squad.run(query)
        self.assertTrue(result.success)
        self.assertEqual(len(result.hops), 3)
        self.assertEqual(result.hops[0].to_agent, "version_worker")
        self.assertEqual(result.hops[1].to_agent, "code_sample_worker")
        self.assertEqual(result.hops[2].to_agent, "client_response")
        self.assertTrue(HANDOFFS_LOG_PATH.exists())

    def test_worker_1_failure_injection_and_orchestrator_degradation(self):
        failing_squad = OrchestratorSquad(force_worker1_500_on_query="q_fail")
        query = {
            "id": "q_fail",
            "question": "Migrate Stream.feed to v3: Check if WebSockets status 101 is supported.",
            "current_version": "v2",
            "target_version": "v3",
        }
        res = failing_squad.run(query)
        self.assertTrue(res.success)
        self.assertIsNotNone(res.failure_handled)
        self.assertEqual(res.failure_handled["injected_error"], "HTTP 500 Internal Server Error")
        self.assertTrue(res.failure_handled["attempted_retry"])
        self.assertFalse(res.failure_handled["hallucinated"])
        self.assertIn("[WARNING] DEGRADED ANSWER", res.notes)

    def test_a2a_task_state_machine_transitions(self):
        sm = A2ATaskStateMachine("task-100")
        self.assertEqual(sm.state, A2ATaskState.SUBMITTED)

        # Transition to WORKING
        state = sm.transition(A2ATaskState.WORKING, "Delegated to Worker 1")
        self.assertEqual(state, A2ATaskState.WORKING)

        # Injected 500 failure transitions to PAUSED: input-required
        state = sm.transition(
            A2ATaskState.PAUSED_INPUT_REQUIRED,
            "Worker 1 HTTP 500 encountered; requesting target SDK version confirmation",
        )
        self.assertEqual(state, A2ATaskState.PAUSED_INPUT_REQUIRED)

        # Resuming back to WORKING
        state = sm.transition(A2ATaskState.WORKING, "Caller provided target_version='v3'")
        self.assertEqual(state, A2ATaskState.WORKING)

        # Completion
        state = sm.transition(A2ATaskState.COMPLETED, "Worker 2 generated verified v3 code")
        self.assertEqual(state, A2ATaskState.COMPLETED)
        self.assertEqual(len(sm.history), 5)

    def test_agent_card_schema(self):
        self.assertEqual(ORCHESTRATOR_AGENT_CARD["agent_id"], "urn:agent:devdocs:orchestrator-squad")
        self.assertEqual(len(ORCHESTRATOR_AGENT_CARD["capabilities"]), 3)
        self.assertIn("input_schema", ORCHESTRATOR_AGENT_CARD["interfaces"])
        self.assertIn("output_schema", ORCHESTRATOR_AGENT_CARD["interfaces"])
        self.assertEqual(ORCHESTRATOR_AGENT_CARD["authentication"]["type"], "bearer_token")


if __name__ == "__main__":
    unittest.main(verbosity=2)
