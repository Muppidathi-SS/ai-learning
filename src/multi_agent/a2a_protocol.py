"""
Bonus Challenge: Agent-to-Agent (A2A) Protocol Layer & AgentCard Specification.
Defines:
  1. Orchestrator AgentCard (capabilities, interfaces, auth).
  2. A2A Task State Machine mapping the HTTP 500 error to PAUSED: input-required.
  3. Two-line protocol value statement.
"""

from enum import Enum
import json
from typing import Any, Dict, List, Optional


class A2ATaskState(str, Enum):
    SUBMITTED = "SUBMITTED"
    WORKING = "WORKING"
    PAUSED_INPUT_REQUIRED = "PAUSED: input-required"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Formal AgentCard definition according to A2A specification
ORCHESTRATOR_AGENT_CARD = {
    "agent_id": "urn:agent:devdocs:orchestrator-squad",
    "name": "SDK Migration Orchestrator Squad",
    "version": "1.0.0",
    "description": (
        "Orchestrator coordinating Version/Deprecation and Code Sample specialists "
        "for automated developer SDK migration analysis across v1, v2, and v3 APIs."
    ),
    "capabilities": [
        {
            "skill": "sdk_migration_orchestration",
            "description": "Decomposes migration query and coordinates specialist workers."
        },
        {
            "skill": "version_deprecation_audit",
            "description": "Audits symbol deprecations and sunset timelines."
        },
        {
            "skill": "openapi_code_synthesis",
            "description": "Synthesizes executable migration code samples grounded in OpenAPI schemas."
        }
    ],
    "interfaces": {
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Developer migration question"},
                "current_sdk_version": {"type": "string", "enum": ["v1", "v2"], "default": "v2"},
                "target_sdk_version": {"type": "string", "enum": ["v2", "v3"], "default": "v3"}
            },
            "required": ["query"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "v3_code": {"type": "string", "description": "Synthesized Python migration code"},
                "deprecated_symbols": {"type": "array", "items": {"type": "string"}},
                "task_state": {"type": "string", "enum": [s.value for s in A2ATaskState]},
                "notes": {"type": "string"}
            },
            "required": ["v3_code", "task_state"]
        }
    },
    "authentication": {
        "type": "bearer_token",
        "scope": "sdk:migrate:execute",
        "issuer": "https://auth.internal.company.net/v1/tokens"
    }
}


class A2ATaskStateMachine:
    """Manages the formal A2A task lifecycle and state transitions."""

    def __init__(self, task_id: str, query: str = ""):
        self.task_id = task_id
        self.query = query
        self.current_state = A2ATaskState.SUBMITTED
        self.state_history: List[Dict[str, Any]] = [
            {"state": self.current_state.value, "timestamp": "T0", "event": "Task received"}
        ]
        self.pending_input_prompt: Optional[str] = None

    @property
    def state(self) -> A2ATaskState:
        return self.current_state

    @property
    def history(self) -> List[Dict[str, Any]]:
        return self.state_history

    def transition(self, new_state: A2ATaskState, event: str, payload: Optional[Dict[str, Any]] = None) -> A2ATaskState:
        self.current_state = new_state
        entry = {
            "state": new_state.value,
            "event": event,
            "payload": payload or {},
        }
        self.state_history.append(entry)
        return self.current_state

    def handle_worker1_http_500(self, error_message: str):
        """
        Maps the HTTP 500 failure onto the A2A task lifecycle:
        Instead of crashing as FAILED, transitions to PAUSED: input-required to solicit user target version.
        """
        self.pending_input_prompt = (
            f"Deprecation registry lookup failed ({error_message}). "
            "Please confirm or provide your target SDK version (e.g. 'v3') to proceed with code generation."
        )
        self.transition(
            A2ATaskState.PAUSED_INPUT_REQUIRED,
            event="Worker 1 returned HTTP 500 Internal Server Error",
            payload={"pending_input_prompt": self.pending_input_prompt}
        )

    def resume_with_user_input(self, user_version_confirmation: str):
        """Resumes a paused task once the caller supplies the requested confirmation."""
        self.transition(
            A2ATaskState.WORKING,
            event=f"Caller confirmed target version '{user_version_confirmation}'",
            payload={"target_version": user_version_confirmation}
        )
        self.pending_input_prompt = None
        self.transition(
            A2ATaskState.COMPLETED,
            event="Code generation completed with confirmed user version."
        )


# Protocol Value Statement (Exactly 2 Lines)
A2A_PROTOCOL_VALUE_STATEMENT = (
    "Line 1: Formal A2A protocols provide standardized task state lifecycles (such as PAUSED: input-required, async polling, and cancellation) and schema-negotiated capability discovery (AgentCards) that generic point-to-point REST endpoints lack.\n"
    "Line 2: They decouple agent identity, contract validation, and multi-turn context boundaries, preventing brittle, ad-hoc glue code from proliferating as agent topologies evolve."
)
