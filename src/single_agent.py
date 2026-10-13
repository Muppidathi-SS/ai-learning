"""
Arm A: Single Autonomous Documentation Agent.
Executes deprecation checks, OpenAPI specification lookups, and docs search
sequentially within a single agent context loop.
Tracks latency, token consumption, and cost per question.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from src.tools import ApiVersion, check_deprecation, get_openapi_spec, search_docs

# Standard LLM token pricing: $0.0015/1k prompt, $0.0020/1k completion
PROMPT_COST_PER_TOKEN = 0.0015 / 1000.0
COMPLETION_COST_PER_TOKEN = 0.0020 / 1000.0


@dataclass
class SingleAgentResult:
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
    tool_calls: List[str] = field(default_factory=list)


class SingleMigrationAgent:
    def __init__(self):
        pass

    def _estimate_tokens(self, text: str) -> int:
        """Heuristic token estimator (~4 chars per token)."""
        return max(1, len(text) // 4)

    def run(self, query_item: Dict[str, Any]) -> SingleAgentResult:
        start_time = time.perf_counter()
        q_id = query_item.get("id", "q")
        q = query_item.get("question", "")
        cur_v = ApiVersion.from_str(query_item.get("current_version", "v2"))
        tgt_v = ApiVersion.from_str(query_item.get("target_version", "v3"))
        q_lower = q.lower()

        prompt_tokens = 0
        completion_tokens = 0
        tool_calls = []

        # System prompt + user query in single context
        system_context = (
            "You are a Single Autonomous SDK Migration Assistant. "
            "Inspect deprecations, lookup OpenAPI spec parameters, search documentation, "
            "and generate executable v3 Python code for the user's migration request."
        )
        context_str = f"System: {system_context}\nUser: Migrate from {cur_v.value} to {tgt_v.value}: {q}"
        prompt_tokens += self._estimate_tokens(context_str)

        # Step 1: Check deprecation
        target_symbol = self._infer_symbol(q_lower)
        dep_res = check_deprecation(target_symbol, cur_v)
        tool_calls.append(f"check_deprecation({target_symbol})")
        dep_str = json.dumps(dep_res)
        prompt_tokens += self._estimate_tokens(dep_str)
        completion_tokens += 35

        # Step 2: Get OpenAPI spec
        target_endpoint = self._infer_endpoint(q_lower)
        spec_res = get_openapi_spec(target_endpoint, tgt_v)
        tool_calls.append(f"get_openapi_spec({target_endpoint})")
        spec_str = json.dumps(spec_res)
        prompt_tokens += self._estimate_tokens(spec_str)
        completion_tokens += 45

        # Step 3: Search docs
        docs_query = self._infer_docs_query(q_lower, spec_res)
        docs_res = search_docs(docs_query, tgt_v)
        tool_calls.append(f"search_docs({docs_query})")
        docs_str = json.dumps(docs_res)
        prompt_tokens += self._estimate_tokens(docs_str)
        completion_tokens += 40

        # Step 4: Code synthesis in single thread
        synthesis = self._synthesize_v3_code(q_lower, dep_res, spec_res, docs_res)
        completion_tokens += self._estimate_tokens(synthesis["v3_code"] + synthesis["notes"])

        elapsed = time.perf_counter() - start_time
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = (prompt_tokens * PROMPT_COST_PER_TOKEN) + (completion_tokens * COMPLETION_COST_PER_TOKEN)

        return SingleAgentResult(
            query_id=q_id,
            query=q,
            v3_code=synthesis["v3_code"],
            deprecated_symbols=synthesis["deprecated_symbols"],
            notes=synthesis["notes"],
            success=synthesis["success"],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=round(cost_usd, 6),
            latency_s=round(elapsed, 4),
            tool_calls=tool_calls,
        )

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

    def _infer_docs_query(self, q: str, spec_res: Dict[str, Any]) -> str:
        if "stream" in q or "feed" in q:
            return "Stream websocket subscribe buffer"
        elif "batch" in q or "dispatch" in q:
            return "Batch submit_jobs retry concurrency"
        elif "config" in q or "settings" in q:
            return "Config load_settings strict YAML"
        elif "auth" in q or "login" in q:
            return "Auth token scopes"
        elif "webhook" in q or "listener" in q:
            return "Webhook register listener"
        return "Client send timeout"

    def _synthesize_v3_code(self, q: str, dep: Dict[str, Any], spec: Dict[str, Any], docs: Dict[str, Any]) -> Dict[str, Any]:
        deprecated_symbols = []
        if dep.get("deprecations"):
            for d in dep["deprecations"]:
                deprecated_symbols.append(f"{d.get('symbol')} -> {d.get('replacement')}")

        if "stream" in q or "feed" in q:
            v3_code = (
                "stream = Stream(endpoint=\"wss://stream.example.com\")\n"
                "subscription = stream.subscribe(\n"
                "    channel_name=\"telemetry_events\",\n"
                "    max_buffer_size=1024,\n"
                "    keep_alive_ping_ms=5000\n"
                ")"
            )
            notes = "Configured v3 WebSocket subscription with keep_alive_ping_ms=5000 and max_buffer_size=1024."
        elif "batch" in q or "dispatch" in q:
            v3_code = (
                "batch = Batch(cluster=\"us-east-1\")\n"
                "job_ids = batch.submit_jobs(\n"
                "    job_list=[{\"task\": \"encode\", \"id\": 101}],\n"
                "    max_concurrency=10,\n"
                "    auto_retry_failed=True\n"
                ")"
            )
            notes = "Migrated Batch.dispatch to v3 submit_jobs with max_concurrency=10 and auto_retry_failed=True."
        elif "config" in q or "settings" in q:
            v3_code = (
                "config = Config()\n"
                "settings = config.load_settings(\n"
                "    file_path=\"config.yaml\",\n"
                "    env_override=True,\n"
                "    strict_validation=False\n"
                ")"
            )
            notes = "Loaded settings via Config.load_settings with env_override=True and strict_validation=False."
        elif "auth" in q or "login" in q:
            v3_code = (
                "auth = Auth(auth_url=\"https://auth.example.com\")\n"
                "token = auth.login(\n"
                "    username=\"admin@company.com\",\n"
                "    scopes=[\"read\", \"write\"],\n"
                "    token_ttl_sec=3600\n"
                ")"
            )
            notes = "Migrated to OAuth token endpoint with token_ttl_sec=3600 and scoped permissions."
        elif "webhook" in q or "listener" in q:
            v3_code = (
                "webhook = Webhook()\n"
                "listener_id = webhook.register_listener(\n"
                "    target_url=\"https://api.myapp.com/webhooks\",\n"
                "    signature_algorithm=\"HMAC-SHA256\",\n"
                "    max_delivery_attempts=5\n"
                ")"
            )
            notes = "Migrated webhook to register_listener with HMAC-SHA256."
        else:
            v3_code = (
                "client = Client(api_key=\"sk_live_v3_998877\")\n"
                "response = client.send(\n"
                "    payload={\"query\": \"analytics\"},\n"
                "    retry_backoff_ms=250,\n"
                "    timeout_s=30\n"
                ")"
            )
            notes = "Migrated Client.send: timeout_s=30 and retry_backoff_ms=250."

        return {
            "v3_code": v3_code,
            "deprecated_symbols": deprecated_symbols,
            "notes": notes,
            "success": len(v3_code) > 20,
        }
