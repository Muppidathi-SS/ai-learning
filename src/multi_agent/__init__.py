"""Multi-Agent & A2A package initialization."""
from src.multi_agent.orchestrator import OrchestratorSquad, DelegationHop, OrchestratorSquadResult
from src.multi_agent.workers import VersionDeprecationWorker, CodeSampleWorker
from src.multi_agent.a2a_protocol import (
    ORCHESTRATOR_AGENT_CARD,
    A2ATaskState,
    A2ATaskStateMachine,
    A2A_PROTOCOL_VALUE_STATEMENT,
)
