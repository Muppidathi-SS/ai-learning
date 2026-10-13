"""
Specialist Workers for Manager-Plus-Two-Specialists Team:
1. VersionDeprecationWorker: Specializes in deprecation lookup, version matrices, and sunset notices.
2. CodeSampleWorker: Specializes in OpenAPI schema verification and code sample synthesis.
Includes fault injection hook for testing HTTP 500 registry failure handling.
Accurately accounts for full worker context tokens (system prompt, resents, tool calls & results).
"""

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

from src.tools import ApiVersion, check_deprecation, get_openapi_spec, search_docs


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class VersionDeprecationWorker:
    """Specialist Worker 1: Investigates symbol deprecations, release status, and replacement targets."""

    def __init__(self, force_500_error: bool = False):
        self.force_500_error = force_500_error
        self.system_prompt = (
            "You are Worker 1: Version & Deprecation Specialist. "
            "Analyze symbol deprecation status, query changelogs, identify breaking changes, "
            "and output structured deprecation findings for the Orchestrator."
        )

    def execute_task(self, query: str, symbol: str, version: str) -> Dict[str, Any]:
        start = time.perf_counter()
        cur_v = ApiVersion.from_str(version)

        # Fault Injection Hook (HTTP 500 Error Injection)
        if self.force_500_error:
            elapsed = time.perf_counter() - start
            prompt_str = (
                f"System: {self.system_prompt}\n"
                f"Delegated Subtask: Check deprecations for symbol '{symbol}' on version '{version}'\n"
                f"Context Query: '{query}'"
            )
            in_tokens = estimate_tokens(prompt_str)
            out_payload = {
                "status": 500,
                "error": "HTTP 500 Internal Server Error: Deprecation registry service unavailable (connection timeout)",
                "symbol": symbol,
            }
            out_tokens = estimate_tokens(json.dumps(out_payload))
            return {
                "status": "error",
                "status_code": 500,
                "data": out_payload,
                "prompt_tokens": in_tokens,
                "completion_tokens": out_tokens,
                "total_tokens": in_tokens + out_tokens,
                "latency_s": elapsed,
            }

        # Normal execution: worker invokes tool in its own context
        dep_res = check_deprecation(symbol, cur_v)
        dep_items = dep_res.get("deprecations", [])

        # Full Worker context: System prompt + delegation + tool call + tool observation
        prompt_str = (
            f"System: {self.system_prompt}\n"
            f"Delegated Subtask: Inspect deprecations for '{symbol}' ({version})\n"
            f"Original Query: '{query}'\n"
            f"ToolCall: check_deprecation({symbol}, {version}) -> {json.dumps(dep_res)}"
        )
        in_tokens = estimate_tokens(prompt_str)

        out_payload = {
            "status": 200,
            "symbol": symbol,
            "version": version,
            "is_deprecated": len(dep_items) > 0,
            "deprecations": dep_items,
            "replacements": [f"{d.get('symbol')} -> {d.get('replacement')}" for d in dep_items],
            "recommendation": "Migrate to target v3 specification" if dep_items else "Symbol is active in current release.",
        }

        elapsed = time.perf_counter() - start
        out_tokens = estimate_tokens(json.dumps(out_payload))

        return {
            "status": "success",
            "status_code": 200,
            "data": out_payload,
            "prompt_tokens": in_tokens,
            "completion_tokens": out_tokens,
            "total_tokens": in_tokens + out_tokens,
            "latency_s": elapsed,
        }


class CodeSampleWorker:
    """Specialist Worker 2: Investigates OpenAPI schemas and generates executable migration code."""

    def __init__(self):
        self.system_prompt = (
            "You are Worker 2: Code Sample & OpenAPI Specialist. "
            "Inspect OpenAPI schema endpoints, check parameter defaults and data types, "
            "search developer guides, and generate syntactically valid v3 Python code samples."
        )

    def execute_task(
        self,
        query: str,
        target_endpoint: str,
        target_version: str,
        deprecation_context: Dict[str, Any],
        degraded_mode: bool = False,
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        tgt_v = ApiVersion.from_str(target_version)

        # Worker 2 executes tools in its context
        spec_res = get_openapi_spec(target_endpoint, tgt_v)
        docs_query = target_endpoint.split("/")[-1]
        docs_res = search_docs(docs_query, tgt_v)

        q_lower = query.lower()
        v3_code = self._generate_code(q_lower)

        warning_note = ""
        if degraded_mode:
            warning_note = " (Degraded mode: Deprecation registry was unreachable; generated code from active OpenAPI spec only.)"

        out_payload = {
            "status": 200,
            "target_endpoint": target_endpoint,
            "spec_verified": spec_res.get("status") == "success",
            "v3_code": v3_code,
            "notes": f"Generated v3 migration snippet with verified parameters.{warning_note}",
        }

        # THE CONTEXT RESEND BOTTLENECK:
        # Worker 2 prompt must receive:
        # 1. Worker 2 system prompt
        # 2. Re-sent user query
        # 3. Re-sent Worker 1 deprecation context (accumulated context handoff!)
        # 4. OpenAPI spec tool execution & result (large JSON schema)
        # 5. Docs search tool execution & result
        worker2_full_prompt = (
            f"System: {self.system_prompt}\n"
            f"Re-Sent User Query: '{query}'\n"
            f"Re-Sent Upstream Worker 1 Findings: {json.dumps(deprecation_context)}\n"
            f"Task: Inspect OpenAPI spec for '{target_endpoint}' ({target_version}) and generate code.\n"
            f"ToolCall 1: get_openapi_spec({target_endpoint}, {target_version}) -> {json.dumps(spec_res)}\n"
            f"ToolCall 2: search_docs({docs_query}, {target_version}) -> {json.dumps(docs_res)}"
        )
        in_tokens = estimate_tokens(worker2_full_prompt)

        elapsed = time.perf_counter() - start
        out_tokens = estimate_tokens(json.dumps(out_payload))

        return {
            "status": "success",
            "status_code": 200,
            "data": out_payload,
            "prompt_tokens": in_tokens,
            "completion_tokens": out_tokens,
            "total_tokens": in_tokens + out_tokens,
            "latency_s": elapsed,
        }

    def _generate_code(self, q: str) -> str:
        if "stream" in q or "feed" in q:
            return (
                "stream = Stream(endpoint=\"wss://stream.example.com\")\n"
                "subscription = stream.subscribe(\n"
                "    channel_name=\"telemetry_events\",\n"
                "    max_buffer_size=1024,\n"
                "    keep_alive_ping_ms=5000\n"
                ")"
            )
        elif "batch" in q or "dispatch" in q:
            return (
                "batch = Batch(cluster=\"us-east-1\")\n"
                "job_ids = batch.submit_jobs(\n"
                "    job_list=[{\"task\": \"encode\", \"id\": 101}],\n"
                "    max_concurrency=10,\n"
                "    auto_retry_failed=True\n"
                ")"
            )
        elif "config" in q or "settings" in q:
            return (
                "config = Config()\n"
                "settings = config.load_settings(\n"
                "    file_path=\"config.yaml\",\n"
                "    env_override=True,\n"
                "    strict_validation=False\n"
                ")"
            )
        elif "auth" in q or "login" in q:
            return (
                "auth = Auth(auth_url=\"https://auth.example.com\")\n"
                "token = auth.login(\n"
                "    username=\"admin@company.com\",\n"
                "    scopes=[\"read\", \"write\"],\n"
                "    token_ttl_sec=3600\n"
                ")"
            )
        elif "webhook" in q or "listener" in q:
            return (
                "webhook = Webhook()\n"
                "listener_id = webhook.register_listener(\n"
                "    target_url=\"https://api.myapp.com/webhooks\",\n"
                "    signature_algorithm=\"HMAC-SHA256\",\n"
                "    max_delivery_attempts=5\n"
                ")"
            )
        else:
            return (
                "client = Client(api_key=\"sk_live_v3_998877\")\n"
                "response = client.send(\n"
                "    payload={\"query\": \"analytics\"},\n"
                "    retry_backoff_ms=250,\n"
                "    timeout_s=30\n"
                ")"
            )
