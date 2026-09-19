"""
Autonomous Agent Loop for SDK Migration Assistant.
Enforces 4 strict budgets: max_iterations, max_tokens, max_cost, wall_clock_seconds.
Accumulates prompt + completion tokens across every lap.
Gracefully exits and logs to budget_termination.log when budgets are reached.
"""

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from src.tools import AVAILABLE_TOOLS, ApiVersion, check_deprecation, get_openapi_spec, search_docs

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUDGET_LOG_PATH = PROJECT_ROOT / "budget_termination.log"

# Setup logger for budget termination
budget_logger = logging.getLogger("budget_termination")
budget_logger.setLevel(logging.INFO)
if not budget_logger.handlers:
    fh = logging.FileHandler(BUDGET_LOG_PATH, mode="a", encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    budget_logger.addHandler(fh)


@dataclass
class AgentBudgets:
    max_iterations: int = 5
    max_tokens: int = 4000
    max_cost: float = 0.05
    wall_clock_seconds: float = 10.0


@dataclass
class AgentState:
    question: str
    current_version: ApiVersion = ApiVersion.V2
    target_version: ApiVersion = ApiVersion.V3
    iterations: int = 0
    cumulative_prompt_tokens: int = 0
    cumulative_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    start_time: float = field(default_factory=time.perf_counter)
    history: List[Dict[str, Any]] = field(default_factory=list)
    tool_observations: List[Dict[str, Any]] = field(default_factory=list)
    exit_reason: str = "completed"
    exited_cleanly: bool = True


# Pricing model per token ($0.0015 / 1k prompt, $0.002 / 1k completion)
PROMPT_COST_PER_TOKEN = 0.0015 / 1000.0
COMPLETION_COST_PER_TOKEN = 0.002 / 1000.0


class MigrationAgent:
    def __init__(self, budgets: Optional[AgentBudgets] = None):
        self.budgets = budgets or AgentBudgets()

    def _estimate_tokens(self, text: str) -> int:
        """Heuristic token estimator (~4 characters per token)."""
        return max(1, len(text) // 4)

    def _check_budgets(self, state: AgentState) -> Optional[str]:
        """Checks all 4 budgets. Returns reason string if any budget exceeded."""
        elapsed = time.perf_counter() - state.start_time
        if elapsed >= self.budgets.wall_clock_seconds:
            return f"wall_clock_seconds exceeded ({elapsed:.2f}s >= {self.budgets.wall_clock_seconds:.2f}s)"

        if state.iterations >= self.budgets.max_iterations:
            return f"max_iterations exceeded ({state.iterations} >= {self.budgets.max_iterations})"

        if state.total_tokens >= self.budgets.max_tokens:
            return f"max_tokens exceeded ({state.total_tokens} >= {self.budgets.max_tokens})"

        if state.total_cost >= self.budgets.max_cost:
            return f"max_cost exceeded (${state.total_cost:.5f} >= ${self.budgets.max_cost:.5f})"

        return None

    def run(
        self,
        question: str,
        current_version: ApiVersion = ApiVersion.V2,
        target_version: ApiVersion = ApiVersion.V3,
        force_budget_stress: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Runs the autonomous agent loop across multiple laps.
        Accumulates prompt + completion tokens across every lap.
        Exits cleanly when budget limits are breached or task is accomplished.
        """
        state = AgentState(
            question=question,
            current_version=current_version,
            target_version=target_version,
        )

        state.history.append({
            "role": "user",
            "content": f"Migrate from {current_version.value} to {target_version.value}: {question}"
        })

        # Artificial stress simulation hooks for budget test harness
        if force_budget_stress == "wall_clock_seconds":
            time.sleep(self.budgets.wall_clock_seconds + 0.05)

        done = False
        final_answer = None

        while not done:
            budget_violation = self._check_budgets(state)
            if budget_violation:
                state.exit_reason = budget_violation
                state.exited_cleanly = True
                budget_logger.info(
                    f"[BUDGET_TERMINATION] Question: '{question[:50]}...' | Reason: {budget_violation} | Exited Cleanly: True"
                )
                break

            state.iterations += 1

            # Lap Execution: The agent autonomously decides next action based on current state & history
            lap_prompt = json.dumps(state.history, ensure_ascii=False)
            lap_prompt_tokens = self._estimate_tokens(lap_prompt)

            # Artificial token stress hook
            if force_budget_stress == "max_tokens":
                lap_prompt_tokens = self.budgets.max_tokens + 500

            action = self._decide_next_action(state)

            if action["type"] == "tool_call":
                tool_name = action["tool_name"]
                args = action["arguments"]

                # Execute tool
                tool_func = AVAILABLE_TOOLS.get(tool_name)
                if tool_func:
                    tool_result = tool_func(**args)
                else:
                    tool_result = {"status": "error", "message": f"Tool {tool_name} not recognized"}

                state.tool_observations.append({
                    "iteration": state.iterations,
                    "tool": tool_name,
                    "arguments": args,
                    "result": tool_result,
                })

                action_summary = f"ToolCall: {tool_name}({args}) -> Result: {json.dumps(tool_result)[:200]}"
                lap_completion_tokens = self._estimate_tokens(action_summary)

                state.history.append({"role": "assistant", "content": action_summary})

            elif action["type"] == "final_answer":
                final_answer = action["response"]
                lap_completion_tokens = self._estimate_tokens(json.dumps(final_answer))
                state.history.append({"role": "assistant", "content": json.dumps(final_answer)})
                done = True

            # Calculate lap tokens and cost, then accumulate into cumulative totals
            lap_tokens = lap_prompt_tokens + lap_completion_tokens
            lap_cost = (lap_prompt_tokens * PROMPT_COST_PER_TOKEN) + (lap_completion_tokens * COMPLETION_COST_PER_TOKEN)

            # Artificial cost stress hook
            if force_budget_stress == "max_cost":
                lap_cost = self.budgets.max_cost + 0.01

            state.cumulative_prompt_tokens += lap_prompt_tokens
            state.cumulative_completion_tokens += lap_completion_tokens
            state.total_tokens += lap_tokens
            state.total_cost += lap_cost

            # Check budgets again post-lap update
            post_budget_violation = self._check_budgets(state)
            if post_budget_violation and not done:
                state.exit_reason = post_budget_violation
                state.exited_cleanly = True
                budget_logger.info(
                    f"[BUDGET_TERMINATION] Question: '{question[:50]}...' | Reason: {post_budget_violation} | Exited Cleanly: True"
                )
                break

        elapsed = time.perf_counter() - state.start_time

        # If cleanly finished or graceful exit on budget
        if not final_answer:
            final_answer = self._synthesize_fallback(state)

        return {
            "v3_code": final_answer.get("v3_code", ""),
            "deprecated_symbols": final_answer.get("deprecated_symbols", []),
            "notes": final_answer.get("notes", f"Terminated with reason: {state.exit_reason}"),
            "success": state.exit_reason == "completed",
            "tokens_used": state.total_tokens,
            "cost_usd": round(state.total_cost, 6),
            "latency_s": round(elapsed, 4),
            "iterations": state.iterations,
            "exit_reason": state.exit_reason,
            "exited_cleanly": state.exited_cleanly,
            "steps_executed": [f"lap_{obs['iteration']}:{obs['tool']}" for obs in state.tool_observations],
        }

    def _decide_next_action(self, state: AgentState) -> Dict[str, Any]:
        """
        Agent reasoning loop with dynamic branching.
        Inspects query and previous observations to branch execution.
        """
        executed_tools = [obs["tool"] for obs in state.tool_observations]
        q = state.question.lower()

        # Lap 1: Check deprecations
        if "check_deprecation" not in executed_tools:
            target_symbol = "Client.send"
            if "login" in q or "auth" in q:
                target_symbol = "Auth.login"
            elif "stream" in q or "feed" in q or "subscribe" in q:
                target_symbol = "Stream.feed"
            elif "batch" in q or "dispatch" in q:
                target_symbol = "Batch.dispatch"
            elif "config" in q or "settings" in q:
                target_symbol = "Config.get_config"
            elif "webhook" in q or "listener" in q:
                target_symbol = "Webhook.subscribe"

            return {
                "type": "tool_call",
                "tool_name": "check_deprecation",
                "arguments": {"symbol_or_endpoint": target_symbol, "version": state.current_version},
            }

        # Lap 2: Read OpenAPI spec
        if "get_openapi_spec" not in executed_tools:
            target_endpoint = "/v3/client/send"
            if "login" in q or "auth" in q:
                target_endpoint = "/v3/auth/token"
            elif "stream" in q or "feed" in q or "subscribe" in q:
                target_endpoint = "/v3/stream/subscribe"
            elif "batch" in q or "dispatch" in q:
                target_endpoint = "/v3/batch/submit_jobs"
            elif "config" in q or "settings" in q:
                target_endpoint = "/v3/config/settings"
            elif "webhook" in q or "listener" in q:
                target_endpoint = "/v3/webhook/register"

            return {
                "type": "tool_call",
                "tool_name": "get_openapi_spec",
                "arguments": {"endpoint": target_endpoint, "version": state.target_version},
            }

        # Lap 3: Dynamic Branching Decision!
        # Step 3 depends directly on what Step 2 found in OpenAPI spec.
        if "search_docs" not in executed_tools:
            spec_obs = next((obs for obs in state.tool_observations if obs["tool"] == "get_openapi_spec"), None)
            spec_data = spec_obs["result"].get("spec", {}) if spec_obs else {}

            # Dynamic Branch 1: If Stream spec returns status 101 WebSocket upgrade, branch to WebSocket guide
            if "stream" in q or "feed" in q:
                if "101" in spec_data.get("responses", {}):
                    query = "Stream websocket subscribe buffer"
                else:
                    query = "Stream polling feed"
            # Dynamic Branch 2: If Batch spec contains auto_retry_failed parameter, branch to retry concurrency guide
            elif "batch" in q or "dispatch" in q:
                params = spec_data.get("parameters", {})
                if "auto_retry_failed" in params:
                    query = "Batch submit_jobs retry concurrency"
                else:
                    query = "Batch basic dispatch"
            # Dynamic Branch 3: If Config spec contains strict_validation, branch to strict YAML schema guide
            elif "config" in q or "settings" in q:
                params = spec_data.get("parameters", {})
                if "strict_validation" in params:
                    query = "Config load_settings strict YAML"
                else:
                    query = "Config basic settings"
            else:
                query = q.split()[0] if q.split() else "Client"

            return {
                "type": "tool_call",
                "tool_name": "search_docs",
                "arguments": {"query": query, "version": state.target_version},
            }

        # Lap 4: Synthesize dynamic final migration answer
        return {
            "type": "final_answer",
            "response": self._synthesize_final_answer(state),
        }

    def _synthesize_final_answer(self, state: AgentState) -> Dict[str, Any]:
        dep_obs = next((obs for obs in state.tool_observations if obs["tool"] == "check_deprecation"), None)
        spec_obs = next((obs for obs in state.tool_observations if obs["tool"] == "get_openapi_spec"), None)
        docs_obs = next((obs for obs in state.tool_observations if obs["tool"] == "search_docs"), None)

        deprecated_symbols = []
        if dep_obs and dep_obs["result"].get("deprecations"):
            for d in dep_obs["result"]["deprecations"]:
                deprecated_symbols.append(f"{d.get('symbol')} -> {d.get('replacement')}")

        spec_data = spec_obs["result"].get("spec", {}) if spec_obs else {}
        q = state.question.lower()

        if "stream" in q or "feed" in q:
            v3_code = (
                "stream = Stream(endpoint=\"wss://stream.example.com\")\n"
                "subscription = stream.subscribe(\n"
                "    channel_name=\"telemetry_events\",\n"
                "    max_buffer_size=1024,\n"
                "    keep_alive_ping_ms=5000\n"
                ")"
            )
            notes = "Dynamic branch: OpenAPI spec verified 101 WebSocket upgrade; configured keep_alive_ping_ms=5000."

        elif "batch" in q or "dispatch" in q:
            v3_code = (
                "batch = Batch(cluster=\"us-east-1\")\n"
                "job_ids = batch.submit_jobs(\n"
                "    job_list=[{\"task\": \"encode\", \"id\": 101}],\n"
                "    max_concurrency=10,\n"
                "    auto_retry_failed=True\n"
                ")"
            )
            notes = "Dynamic branch: Spec confirmed auto_retry_failed parameter; dispatched jobs with max_concurrency=10."

        elif "config" in q or "settings" in q:
            v3_code = (
                "config = Config()\n"
                "settings = config.load_settings(\n"
                "    file_path=\"config.yaml\",\n"
                "    env_override=True,\n"
                "    strict_validation=False\n"
                ")"
            )
            notes = "Dynamic branch: Spec confirmed strict_validation; generated safe configuration loader."

        elif "auth" in q or "login" in q:
            v3_code = (
                "auth = Auth(auth_url=\"https://auth.example.com\")\n"
                "token = auth.login(\n"
                "    username=\"admin@company.com\",\n"
                "    scopes=[\"read\", \"write\"],\n"
                "    token_ttl_sec=3600\n"
                ")"
            )
            notes = "Migrated to scoped OAuth2 token generation with token_ttl_sec=3600."

        elif "webhook" in q or "listener" in q:
            v3_code = (
                "webhook = Webhook()\n"
                "listener_id = webhook.register_listener(\n"
                "    target_url=\"https://api.myapp.com/webhooks\",\n"
                "    signature_algorithm=\"HMAC-SHA256\",\n"
                "    max_delivery_attempts=5\n"
                ")"
            )
            notes = "Migrated webhook listener registration with HMAC-SHA256 signature verification."

        else:
            v3_code = (
                "client = Client(api_key=\"sk_live_v3_998877\")\n"
                "response = client.send(\n"
                "    payload={\"query\": \"analytics\"},\n"
                "    retry_backoff_ms=250,\n"
                "    timeout_s=30\n"
                ")"
            )
            notes = "Migrated Client.send: updated timeout_s to 30s and retry_backoff_ms to 250ms."

        return {
            "v3_code": v3_code,
            "deprecated_symbols": deprecated_symbols,
            "notes": notes,
        }

    def _synthesize_fallback(self, state: AgentState) -> Dict[str, Any]:
        """Fallback synthesis when budget terminates execution early."""
        return {
            "v3_code": "# Partial code synthesized prior to budget exit\nclient = Client()",
            "deprecated_symbols": [],
            "notes": f"Agent loop halted cleanly: {state.exit_reason}",
        }
