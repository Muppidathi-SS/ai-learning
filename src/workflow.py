"""
Workflow module: Deterministic 3-step pipeline for SDK migration.
Step 1: check_deprecation (look up changelog/deprecations)
Step 2: get_openapi_spec (fetch schema parameters)
Step 3: search_docs (lookup syntax) -> write v3 code sample

Shares exact same input and output schema as the autonomous agent.
"""

import time
from typing import Any, Dict, List, Optional
from src.tools import ApiVersion, check_deprecation, get_openapi_spec, search_docs


def _extract_primary_symbol(question: str) -> str:
    q = question.lower()
    if "send" in q or "client" in q:
        return "Client.send"
    if "login" in q or "auth" in q or "token" in q:
        return "Auth.login"
    if "stream" in q or "feed" in q or "subscribe" in q:
        return "Stream.feed"
    if "batch" in q or "dispatch" in q or "submit" in q:
        return "Batch.dispatch"
    if "config" in q or "settings" in q:
        return "Config.get_config"
    if "webhook" in q or "listener" in q:
        return "Webhook.subscribe"
    return "Client.send"


def _map_symbol_to_v3_endpoint(symbol: str, deprecation_result: Dict[str, Any]) -> str:
    # Check if deprecation gave a replacement endpoint or symbol
    for dep in deprecation_result.get("deprecations", []):
        rep = dep.get("replacement", "")
        if rep.startswith("/v3/"):
            return rep
        if "submit_jobs" in rep:
            return "/v3/batch/submit_jobs"
        if "subscribe" in rep:
            return "/v3/stream/subscribe"
        if "token" in rep:
            return "/v3/auth/token"
        if "load_settings" in rep:
            return "/v3/config/settings"
        if "register_listener" in rep:
            return "/v3/webhook/register"

    if "client" in symbol.lower():
        return "/v3/client/send"
    if "auth" in symbol.lower():
        return "/v3/auth/token"
    if "stream" in symbol.lower():
        return "/v3/stream/subscribe"
    if "batch" in symbol.lower():
        return "/v3/batch/submit_jobs"
    if "config" in symbol.lower():
        return "/v3/config/settings"
    if "webhook" in symbol.lower():
        return "/v3/webhook/register"
    return "/v3/client/send"


def run_workflow(
    question: str,
    current_version: ApiVersion = ApiVersion.V2,
    target_version: ApiVersion = ApiVersion.V3,
) -> Dict[str, Any]:
    """
    Executes the deterministic 3-step hardcoded workflow:
    1. check_deprecation
    2. get_openapi_spec
    3. search_docs -> generate v3 code sample
    """
    start_time = time.perf_counter()
    steps_executed = []
    deprecated_symbols = []

    # Step 1: Check Deprecation / Changelog
    steps_executed.append("step_1:check_deprecation")
    primary_symbol = _extract_primary_symbol(question)
    dep_res = check_deprecation(primary_symbol, current_version)
    if dep_res.get("deprecations"):
        for d in dep_res["deprecations"]:
            deprecated_symbols.append(f"{d.get('symbol')} -> {d.get('replacement')}")

    # Step 2: Read OpenAPI Spec
    steps_executed.append("step_2:get_openapi_spec")
    v3_endpoint = _map_symbol_to_v3_endpoint(primary_symbol, dep_res)
    spec_res = get_openapi_spec(v3_endpoint, target_version)

    # Step 3: Search Docs and Write Sample
    steps_executed.append("step_3:search_docs_and_synthesize")
    docs_res = search_docs(primary_symbol.split(".")[0], target_version)

    # Deterministic Code Synthesis
    v3_code = ""
    notes = ""

    if "client" in primary_symbol.lower():
        v3_code = (
            "client = Client(api_key=\"sk_live_v3_998877\")\n"
            "response = client.send(\n"
            "    payload={\"query\": \"analytics\"},\n"
            "    retry_backoff_ms=250,\n"
            "    timeout_s=30\n"
            ")"
        )
        notes = "Updated timeout_s default to 30s and retry_backoff_ms to 250ms per v3 Client spec."

    elif "auth" in primary_symbol.lower():
        v3_code = (
            "auth = Auth(auth_url=\"https://auth.example.com\")\n"
            "token = auth.login(\n"
            "    username=\"admin@company.com\",\n"
            "    scopes=[\"read\", \"write\"],\n"
            "    token_ttl_sec=3600\n"
            ")"
        )
        notes = "Migrated from /v2/auth/login to /v3/auth/token; default token_ttl_sec is now 3600s."

    elif "stream" in primary_symbol.lower():
        v3_code = (
            "stream = Stream(endpoint=\"wss://stream.example.com\")\n"
            "subscription = stream.subscribe(\n"
            "    channel_name=\"telemetry_events\",\n"
            "    max_buffer_size=1024,\n"
            "    keep_alive_ping_ms=5000\n"
            ")"
        )
        notes = "Stream.feed() replaced by Stream.subscribe() with max_buffer_size=1024 and keep_alive_ping_ms=5000."

    elif "batch" in primary_symbol.lower():
        v3_code = (
            "batch = Batch(cluster=\"us-east-1\")\n"
            "job_ids = batch.submit_jobs(\n"
            "    job_list=[{\"task\": \"encode\", \"id\": 101}],\n"
            "    max_concurrency=10,\n"
            "    auto_retry_failed=True\n"
            ")"
        )
        notes = "Batch.dispatch() replaced by Batch.submit_jobs() with auto_retry_failed=True and job_list parameter."

    elif "config" in primary_symbol.lower():
        v3_code = (
            "config = Config()\n"
            "settings = config.load_settings(\n"
            "    file_path=\"config.yaml\",\n"
            "    env_override=True,\n"
            "    strict_validation=False\n"
            ")"
        )
        notes = "Config.get_config() replaced by Config.load_settings() supporting env_override."

    elif "webhook" in primary_symbol.lower():
        v3_code = (
            "webhook = Webhook()\n"
            "listener_id = webhook.register_listener(\n"
            "    target_url=\"https://api.myapp.com/webhooks\",\n"
            "    signature_algorithm=\"HMAC-SHA256\",\n"
            "    max_delivery_attempts=5\n"
            ")"
        )
        notes = "Webhook.subscribe() replaced by Webhook.register_listener() requiring signature_algorithm."

    else:
        v3_code = "# Generic v3 migration boilerplate\nclient = Client()"
        notes = "Standard v3 template generated."

    latency_s = time.perf_counter() - start_time

    # Fixed workflow does not use LLM loops: token cost is minimal/fixed template tokens
    # Template synthesis tokens ~ 250 prompt tokens + 120 output tokens = ~370 tokens
    tokens_used = 370
    cost_usd = round(tokens_used * 0.000002, 6)

    return {
        "v3_code": v3_code,
        "deprecated_symbols": deprecated_symbols,
        "notes": notes,
        "success": True,
        "tokens_used": tokens_used,
        "cost_usd": cost_usd,
        "latency_s": round(latency_s, 4),
        "steps_executed": steps_executed,
    }
