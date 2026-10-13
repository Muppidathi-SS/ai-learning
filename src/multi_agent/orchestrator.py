"""
Manager / Orchestrator Agent for Week 10 Multi-Agent Squad.
Delegates subtasks to VersionDeprecationWorker and CodeSampleWorker.
Logs every agent-to-agent delegation hop and token cost into handoffs.log.
Handles graceful degradation upon upstream HTTP 500 worker failures.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

from src.multi_agent.workers import VersionDeprecationWorker, CodeSampleWorker, estimate_tokens

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HANDOFFS_LOG_PATH = PROJECT_ROOT / "handoffs.log"

PROMPT_COST_PER_TOKEN = 0.0015 / 1000.0
COMPLETION_COST_PER_TOKEN = 0.0020 / 1000.0


@dataclass
class DelegationHop:
    hop_id: str
    query_id: str
    from_agent: str
    to_agent: str
    step_description: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_s: float
    status: str = "SUCCESS"


@dataclass
class OrchestratorSquadResult:
    query_id: str
    query: str
    v3_code: str
    deprecated_symbols: List[str]
    notes: str
    success: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_s: float
    hops: List[DelegationHop] = field(default_factory=list)
    failure_handled: Optional[Dict[str, Any]] = None


class OrchestratorSquad:
    """
    Manager-Plus-Two-Specialists Team:
    - Orchestrator plans subtasks and delegates deprecation checking to Worker 1.
    - Orchestrator re-sends user query + Worker 1 findings to Worker 2 for code generation.
    - Orchestrator aggregates results into the final migration guide.
    """

    def __init__(self, force_worker1_500_on_query: Optional[str] = None):
        self.force_worker1_500_on_query = force_worker1_500_on_query
        self.code_worker = CodeSampleWorker()
        self.all_logged_hops: List[DelegationHop] = []

    def _infer_symbol(self, q: str) -> str:
        if "login" in q or "auth" in q:
            return "Auth.login"
        elif "stream" in q or "feed" in q or "subscribe" in q:
            return "Stream.feed"
        elif "batch" in q or "dispatch" in q:
            return "Batch.dispatch"
        elif "config" in q or "settings" in q:
            return "Config.get_config"
        elif "webhook" in q or "listener" in q:
            return "Webhook.subscribe"
        return "Client.send"

    def _infer_endpoint(self, q: str) -> str:
        if "login" in q or "auth" in q:
            return "/v3/auth/token"
        elif "stream" in q or "feed" in q or "subscribe" in q:
            return "/v3/stream/subscribe"
        elif "batch" in q or "dispatch" in q:
            return "/v3/batch/submit_jobs"
        elif "config" in q or "settings" in q:
            return "/v3/config/settings"
        elif "webhook" in q or "listener" in q:
            return "/v3/webhook/register"
        return "/v3/client/send"

    def _log_hop(self, hop: DelegationHop):
        self.all_logged_hops.append(hop)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        log_line = (
            f"[{timestamp}] [HANDOFF] hop_id={hop.hop_id} | query_id={hop.query_id} | "
            f"from={hop.from_agent} -> to={hop.to_agent} | step=\"{hop.step_description}\" | "
            f"tokens_in={hop.prompt_tokens} | tokens_out={hop.completion_tokens} | "
            f"total_tokens={hop.total_tokens} | cost=${hop.cost_usd:.6f} | status={hop.status}"
        )
        try:
            with open(HANDOFFS_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception:
            pass

    def run(self, query_item: Dict[str, Any]) -> OrchestratorSquadResult:
        start_time = time.perf_counter()
        q_id = query_item.get("id", "q")
        q = query_item.get("question", "")
        cur_v = query_item.get("current_version", "v2")
        tgt_v = query_item.get("target_version", "v3")
        q_lower = q.lower()

        hops: List[DelegationHop] = []
        should_fail_worker1 = (self.force_worker1_500_on_query == q_id)
        version_worker = VersionDeprecationWorker(force_500_error=should_fail_worker1)

        symbol = self._infer_symbol(q_lower)
        endpoint = self._infer_endpoint(q_lower)

        # -------------------------------------------------------------
        # HOP 1: Orchestrator -> Worker 1 (Version & Deprecation Check)
        # -------------------------------------------------------------
        # Orchestrator planning turn + dispatch to Worker 1
        orch_plan_prompt = (
            f"Orchestrator System: Plan migration workflow for query '{q}'. "
            f"Step 1: Delegate deprecation audit of '{symbol}' on version '{cur_v}' to VersionDeprecationWorker."
        )
        orch_plan_tokens = estimate_tokens(orch_plan_prompt)

        worker1_res = version_worker.execute_task(q, symbol, cur_v)
        failure_handled_info = None

        hop1_in = orch_plan_tokens + worker1_res["prompt_tokens"]
        hop1_out = worker1_res["completion_tokens"] + 45  # delegation instruction completion
        hop1_tot = hop1_in + hop1_out
        hop1_cost = (hop1_in * PROMPT_COST_PER_TOKEN) + (hop1_out * COMPLETION_COST_PER_TOKEN)

        if worker1_res["status_code"] == 500:
            hop1 = DelegationHop(
                hop_id=f"{q_id}-HOP-1",
                query_id=q_id,
                from_agent="orchestrator",
                to_agent="version_worker",
                step_description=f"Orchestrator delegates symbol deprecation check for {symbol} ({cur_v})",
                prompt_tokens=hop1_in,
                completion_tokens=hop1_out,
                total_tokens=hop1_tot,
                cost_usd=round(hop1_cost, 6),
                latency_s=worker1_res["latency_s"],
                status="FAILED_HTTP_500",
            )
            hops.append(hop1)
            self._log_hop(hop1)

            # Orchestrator Retry Attempt
            retry_res = version_worker.execute_task(q, symbol, cur_v)
            hop1_retry = DelegationHop(
                hop_id=f"{q_id}-HOP-1-RETRY",
                query_id=q_id,
                from_agent="orchestrator",
                to_agent="version_worker",
                step_description="Orchestrator retries failed version_worker request",
                prompt_tokens=retry_res["prompt_tokens"],
                completion_tokens=retry_res["completion_tokens"],
                total_tokens=retry_res["total_tokens"],
                cost_usd=(retry_res["prompt_tokens"] * PROMPT_COST_PER_TOKEN) + (retry_res["completion_tokens"] * COMPLETION_COST_PER_TOKEN),
                latency_s=retry_res["latency_s"],
                status="RETRY_FAILED_HTTP_500",
            )
            hops.append(hop1_retry)
            self._log_hop(hop1_retry)

            failure_handled_info = {
                "injected_error": "HTTP 500 Internal Server Error",
                "attempted_retry": True,
                "retry_count": 1,
                "degradation_mode": "Partial answer generated; deprecation verification explicitly disclaimed.",
                "hallucinated": False,
            }
            w1_data = {
                "status": "degraded_500",
                "symbol": symbol,
                "is_deprecated": "UNKNOWN (Service 500)",
                "deprecations": [],
                "replacements": [],
                "warning": "Deprecation registry unreachable; could not verify symbol retirement status.",
            }
        else:
            hop1 = DelegationHop(
                hop_id=f"{q_id}-HOP-1",
                query_id=q_id,
                from_agent="orchestrator",
                to_agent="version_worker",
                step_description=f"Orchestrator delegates symbol deprecation check for {symbol} ({cur_v})",
                prompt_tokens=hop1_in,
                completion_tokens=hop1_out,
                total_tokens=hop1_tot,
                cost_usd=round(hop1_cost, 6),
                latency_s=worker1_res["latency_s"],
                status="SUCCESS",
            )
            hops.append(hop1)
            self._log_hop(hop1)
            w1_data = worker1_res["data"]

        # -------------------------------------------------------------
        # HOP 2: Orchestrator -> Worker 2 (Context Re-Send Bottleneck!)
        # -------------------------------------------------------------
        # Orchestrator serializes user query + Worker 1 findings and sends to Worker 2
        degraded = failure_handled_info is not None
        worker2_res = self.code_worker.execute_task(q, endpoint, tgt_v, w1_data, degraded_mode=degraded)

        hop2_in = worker2_res["prompt_tokens"]
        hop2_out = worker2_res["completion_tokens"]
        hop2_tot = hop2_in + hop2_out
        hop2_cost = (hop2_in * PROMPT_COST_PER_TOKEN) + (hop2_out * COMPLETION_COST_PER_TOKEN)

        hop2 = DelegationHop(
            hop_id=f"{q_id}-HOP-2",
            query_id=q_id,
            from_agent="orchestrator",
            to_agent="code_sample_worker",
            step_description=f"Orchestrator re-sends user query + Worker 1 findings to code_sample_worker for {endpoint}",
            prompt_tokens=hop2_in,
            completion_tokens=hop2_out,
            total_tokens=hop2_tot,
            cost_usd=round(hop2_cost, 6),
            latency_s=worker2_res["latency_s"],
            status="SUCCESS",
        )
        hops.append(hop2)
        self._log_hop(hop2)
        w2_data = worker2_res["data"]

        # -------------------------------------------------------------
        # HOP 3: Orchestrator Synthesis & Integration
        # -------------------------------------------------------------
        # Orchestrator absorbs Worker 1 + Worker 2 outputs and synthesizes final answer
        orch_prompt = (
            f"Orchestrator Synthesis: Integrate findings from Worker 1 ({json.dumps(w1_data)}) "
            f"and Worker 2 ({json.dumps(w2_data)}) for user migration request: '{q}'."
        )
        orch_in_tokens = estimate_tokens(orch_prompt)
        v3_code = w2_data["v3_code"]

        if degraded:
            notes = (
                "[WARNING] DEGRADED ANSWER: Deprecation registry service returned HTTP 500. "
                "Generated v3 migration code based on active OpenAPI specification, "
                "but deprecation retirement could not be confirmed. Manual verification required."
            )
        else:
            notes = f"Orchestrator synthesized migration guide: {w2_data['notes']}"

        orch_out_tokens = estimate_tokens(v3_code + notes)
        orch_tot_tokens = orch_in_tokens + orch_out_tokens
        orch_cost = (orch_in_tokens * PROMPT_COST_PER_TOKEN) + (orch_out_tokens * COMPLETION_COST_PER_TOKEN)

        hop3 = DelegationHop(
            hop_id=f"{q_id}-HOP-3",
            query_id=q_id,
            from_agent="orchestrator",
            to_agent="client_response",
            step_description="Orchestrator aggregates specialist outputs into final synthesized migration answer",
            prompt_tokens=orch_in_tokens,
            completion_tokens=orch_out_tokens,
            total_tokens=orch_tot_tokens,
            cost_usd=round(orch_cost, 6),
            latency_s=0.0012,
            status="SUCCESS",
        )
        hops.append(hop3)
        self._log_hop(hop3)

        elapsed = time.perf_counter() - start_time
        total_prompt_tokens = sum(h.prompt_tokens for h in hops)
        total_completion_tokens = sum(h.completion_tokens for h in hops)
        total_tokens = sum(h.total_tokens for h in hops)
        total_cost = sum(h.cost_usd for h in hops)

        deprecated_symbols = w1_data.get("replacements", [])

        return OrchestratorSquadResult(
            query_id=q_id,
            query=q,
            v3_code=v3_code,
            deprecated_symbols=deprecated_symbols,
            notes=notes,
            success=len(v3_code) > 20,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            cost_usd=round(total_cost, 6),
            latency_s=round(elapsed, 4),
            hops=hops,
            failure_handled=failure_handled_info,
        )
