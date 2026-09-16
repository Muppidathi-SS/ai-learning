"""
generate_traces.py
==================
Generates 1,050 realistic production traces representing one week of Developer Documentation
assistant traffic (Mon 2026-09-08 to Mon 2026-09-15).

Schema matches complete replayable trace specification:
- trace_id
- timestamp
- query
- prompt_version
- retrieved_chunks (chunk_id, score, metadata, content)
- model
- model_params
- raw_output
"""

import os
import json
import random
from datetime import datetime, timedelta
from src.chunkers import StructureAwareChunker
from src.indexer import VectorIndexer
from src.retriever import HybridRetriever, VectorRetriever
from src.bm25_retriever import BM25Retriever

def build_indexer():
    chunker = StructureAwareChunker()
    indexer = VectorIndexer()
    indexer.ingest_directory("data/v3", chunker, sdk_version="v3")
    indexer.ingest_directory("data/v2", chunker, sdk_version="v2")
    indexer.ingest_directory("data/v1", chunker, sdk_version="v1")
    return indexer

def get_prompt_template(prompt_version="v1.2.0-system"):
    return (
        "System: You are an expert documentation assistant for the SDK. "
        "Answer the user's question using ONLY the retrieved context chunks below. "
        "If the answer cannot be determined from the chunks, state that it is unavailable in documentation.\n\n"
        "Retrieved Context:\n{context}\n\nUser Question: {query}\nAnswer:"
    )

def simulate_generator(query: str, retrieved_chunks: list) -> str:
    """Deterministic, realistic generation based on top retrieved chunks."""
    if not retrieved_chunks or retrieved_chunks[0]["score"] < 0.01:
        return "REFUSAL: The requested information is not available in the provided documentation corpus."

    top_chunk = retrieved_chunks[0]
    metadata = top_chunk.get("metadata", {})
    chunk_id = top_chunk.get("chunk_id", "")
    content = top_chunk.get("content", "")
    sdk_version = metadata.get("sdk_version", "v3")
    page_id = metadata.get("page_id", "")
    q_lower = query.lower()

    # Out of corpus questions
    if any(k in q_lower for k in ["graphql", "oauth2 refresh token rotation", "rate limit", "payload size in mb", "credit card", "billing"]):
        return "REFUSAL: The requested information is not available in the provided documentation corpus."

    # Specific simulation based on top chunk version and content
    if "retry_backoff_ms" in q_lower or "backoff" in q_lower or "retry delay" in q_lower:
        if "client_v1" in chunk_id or sdk_version == "v1":
            return f"In the Client SDK, the default `retry_backoff_ms` is `1000` milliseconds (1 second) [chunk_id: {chunk_id}, page: {page_id}]."
        elif "client_v2" in chunk_id or sdk_version == "v2":
            return f"In the Client SDK, the default `retry_backoff_ms` parameter is `500` ms for HTTP requests [chunk_id: {chunk_id}, page: {page_id}]."
        else:
            return f"In the v3 Client SDK, the default `retry_backoff_ms` is `250` milliseconds (integer type) [chunk_id: {chunk_id}, page: {page_id}]."

    if "timeout_s" in q_lower or "timeout" in q_lower:
        if "client_v1" in chunk_id or sdk_version == "v1":
            return f"The default `timeout_s` is `120` seconds before the request fails [chunk_id: {chunk_id}, page: {page_id}]."
        elif "client_v2" in chunk_id or sdk_version == "v2":
            return f"The default `timeout_s` is `60` seconds for server responses [chunk_id: {chunk_id}, page: {page_id}]."
        else:
            return f"Exceeding `timeout_s` on `Client.send()` raises a `TimeoutError` after `30` seconds [chunk_id: {chunk_id}, page: {page_id}]."

    if "token_ttl_sec" in q_lower or "token expiration" in q_lower or "session duration" in q_lower:
        if "auth_v1" in chunk_id or sdk_version == "v1":
            return f"The default `token_ttl_sec` parameter for `Auth.login()` is `1800` seconds (30 minutes) [chunk_id: {chunk_id}, page: {page_id}]."
        elif "auth_v2" in chunk_id or sdk_version == "v2":
            return f"The default token lifetime `token_ttl_sec` is `7200` seconds (2 hours) [chunk_id: {chunk_id}, page: {page_id}]."
        else:
            return f"The default `token_ttl_sec` parameter for `Auth.login()` is `3600` seconds (1 hour) [chunk_id: {chunk_id}, page: {page_id}]."

    if "keep_alive_ping_ms" in q_lower or "heartbeat" in q_lower or "ping interval" in q_lower:
        if "stream_v2" in chunk_id or sdk_version == "v2":
            return f"The `Stream.subscribe()` heartbeat interval `keep_alive_ping_ms` defaults to `10000` ms (10 seconds) [chunk_id: {chunk_id}, page: {page_id}]."
        else:
            return f"The default `keep_alive_ping_ms` duration for `Stream.subscribe()` is `5000` milliseconds [chunk_id: {chunk_id}, page: {page_id}]."

    if "max_buffer_size" in q_lower or "buffer size" in q_lower:
        if "stream_v2" in chunk_id or sdk_version == "v2":
            return f"The stream buffer size `max_buffer_size` defaults to `512` messages [chunk_id: {chunk_id}, page: {page_id}]."
        else:
            return f"The stream buffer size `max_buffer_size` defaults to `1024` messages held in memory [chunk_id: {chunk_id}, page: {page_id}]."

    if "scopes" in q_lower or "permission" in q_lower or "login" in q_lower:
        if "auth" in chunk_id:
            return f"For `Auth.login()`, the default authorization scope is `[\"read\"]` of type `list[str]` [chunk_id: {chunk_id}, page: {page_id}]."

    if "max_concurrency" in q_lower or "batch" in q_lower or "submit_jobs" in q_lower:
        if "batch" in chunk_id:
            return f"You can set `max_concurrency` as an integer parameter (default `10`) when calling `Batch.submit_jobs(max_concurrency=10)` [chunk_id: {chunk_id}, page: {page_id}]."

    if "signature_algorithm" in q_lower or "cryptographic algorithm" in q_lower or "webhook" in q_lower or "listener" in q_lower:
        if "webhook" in chunk_id:
            return f"`Webhook.register_listener()` requires the cryptographic signature algorithm `\"HMAC-SHA256\"` [chunk_id: {chunk_id}, page: {page_id}]."

    if "env_override" in q_lower or "config.yaml" in q_lower or "load_settings" in q_lower or "config" in q_lower:
        if "config" in chunk_id:
            return f"`Config.load_settings()` enables environment variable overrides by default (`env_override=True`) with default file `config.yaml` [chunk_id: {chunk_id}, page: {page_id}]."

    # Code example query requesting example but getting method definition
    if any(k in q_lower for k in ["code example", "show me how", "sample code", "python code"]):
        if "struct_003" in chunk_id:
            # Contains actual example code
            if "stream" in chunk_id:
                return (
                    "```python\nstream = Stream(endpoint=\"wss://stream.example.com\")\n"
                    "subscription = stream.subscribe(\n    channel_name=\"telemetry_events\",\n"
                    "    max_buffer_size=1024,\n    keep_alive_ping_ms=5000\n)\n```"
                )
            elif "client" in chunk_id:
                return (
                    "```python\nclient = Client(api_key=\"sk_live_v3_998877\")\n"
                    "response = client.send(payload={\"query\": \"analytics\"}, retry_backoff_ms=250, timeout_s=30)\n```"
                )
            elif "auth" in chunk_id:
                return (
                    "```python\nauth = Auth(auth_url=\"https://auth.example.com\")\ntoken = auth.login(username=\"admin@company.com\", scopes=[\"read\", \"write\"], token_ttl_sec=3600)\n```"
                )
        else:
            # Fallback: returning table summary instead of executable code
            return (
                f"Here are the parameters for `{metadata.get('section', 'Method')}`: "
                f"Refer to {page_id} documentation table [chunk_id: {chunk_id}]."
            )

    return f"Based on {page_id} documentation: {content[:150]}... [chunk_id: {chunk_id}]."

def generate_traces(output_path="traces.jsonl", total_traces=1050):
    print(f"Building indexer and chunk corpus...")
    indexer = build_indexer()
    bm25 = BM25Retriever(indexer.chunks)
    vector_retriever = VectorRetriever(indexer)
    hybrid_retriever = HybridRetriever(vector_retriever, bm25)

    random.seed(20260908)

    # Base pool of diverse user queries representing real production traffic
    query_templates = [
        # Unversioned questions with v1/v2/v3 overlap (triggers wrong-version answers)
        ("What does retry_backoff_ms default to?", None),
        ("What is the default value of retry_backoff_ms on Client.send()?", None),
        ("How many milliseconds is the retry_backoff_ms parameter?", None),
        ("What is the token expiration lifetime token_ttl_sec?", None),
        ("How long is token_ttl_sec valid before expiration in Auth.login?", None),
        ("What is the keep_alive_ping_ms interval for WebSocket stream?", None),
        ("How often does keep_alive_ping_ms ping the server in Stream.subscribe?", None),
        ("What is the default timeout_s in Client.send()?", None),
        ("What is max_buffer_size on Stream.subscribe()?", None),
        
        # Explicit versioned queries
        ("What is the default retry_backoff_ms in v3 Client.send()?", {"sdk_version": "v3"}),
        ("What is token_ttl_sec in v3 Auth.login()?", {"sdk_version": "v3"}),
        ("What is the timeout_s parameter in v3?", {"sdk_version": "v3"}),
        ("What was the legacy timeout_s in v1 Client.send?", {"sdk_version": "v1"}),
        ("What is retry_backoff_ms in the v2 legacy Client.send method?", {"sdk_version": "v2"}),
        
        # Vocabulary divergence / synonyms (often leads to refusal or bad retrieval)
        ("What is the exponential backoff interval when retrying network calls?", None),
        ("How do I set the reconnect delay for network requests?", None),
        ("How long does the user session token stay alive before expiring?", None),
        ("What is the heartbeat ping delay for real-time events?", None),
        ("How do I handle connection timeout errors in the client?", None),
        ("How can I configure worker thread concurrency for bulk jobs?", None),
        
        # Requesting code examples (sometimes receives parameter table struct_002 instead of struct_003)
        ("Show me the Python code example for subscribing to telemetry_events", None),
        ("Provide Python sample code to call Client.send() with retry_backoff_ms", None),
        ("Show me sample code for Auth.login() with scopes", None),
        ("Code example for Batch.submit_jobs in python", None),
        ("Can you show python code to register a webhook listener?", None),
        ("Python code snippet for loading settings from config.yaml", None),
        
        # Scope and permission queries (silently defaults to read-only)
        ("How do I authenticate with admin write permissions using Auth.login()?", None),
        ("What authorization scopes should I pass to Auth.login() for multi-scope access?", None),
        ("How to configure permissions for Auth.login()?", None),
        
        # Cross-class confusion / hallucinated combinations
        ("How to set max_concurrency on Client.send()?", None),
        ("Can I pass auto_retry_failed to Webhook.register_listener()?", None),
        ("Does Stream.subscribe accept env_override?", None),
        ("Can I configure signature_algorithm in Client.send()?", None),
        
        # Specific v3 features (usually works well)
        ("What signing algorithm is used in Webhook.register_listener() -- HMAC-SHA256 or RSA?", None),
        ("Does Config.load_settings() allow environment variable overrides by default?", None),
        ("What is the default config file path config.yaml used by load_settings?", None),
        ("How do you configure max_concurrency for batch job submission?", None),
        ("What is max_delivery_attempts set to by default in Webhook.register_listener()?", None),
        ("What exception class is raised for TimeoutError in the SDK?", None),
        
        # Out-of-corpus questions (should refuse)
        ("What is the maximum HTTP rate limit allowed on the Client.send() endpoint?", None),
        ("How do you configure OAuth2 refresh token rotation for Auth.login()?", None),
        ("What is the maximum payload size in megabytes supported by Webhook.register_listener()?", None),
        ("Does the SDK support GraphQL subscriptions?", None),
        ("How do I update credit card billing details through the SDK?", None),
    ]

    base_time = datetime(2026, 9, 8, 8, 15, 0)
    traces = []

    print(f"Generating {total_traces} production traces...")
    for i in range(1, total_traces + 1):
        trace_id = f"TR-{i:04d}"
        # Increment timestamp across the week
        delta_seconds = int((i / total_traces) * (7 * 24 * 3600)) + random.randint(-120, 120)
        ts = base_time + timedelta(seconds=max(0, delta_seconds))
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Pick query
        q_item = random.choice(query_templates)
        query = q_item[0]
        # Some slight variation in punctuation or casing
        if random.random() < 0.2:
            query = query.lower()
        elif random.random() < 0.1:
            query = query.rstrip("?")

        # Retrieval in production: Hybrid search without version filtering (unless explicitly requested in query)
        filter_dict = q_item[1]
        retrieved_raw = hybrid_retriever.search(query, top_k=3, fusion_pool=25, filter_dict=filter_dict)

        # Build serializable retrieved chunks
        retrieved_chunks = []
        for r in retrieved_raw:
            retrieved_chunks.append({
                "chunk_id": r["chunk_id"],
                "score": round(float(r["score"]), 4),
                "metadata": {
                    "source_file": r["metadata"].get("source_file", ""),
                    "page_id": r["metadata"].get("page_id", ""),
                    "sdk_version": r["metadata"].get("sdk_version", "v3"),
                    "section": r["metadata"].get("section", ""),
                    "anchor": r["metadata"].get("anchor", "")
                },
                "content": r["content"]
            })

        # Generate output
        raw_output = simulate_generator(query, retrieved_chunks)

        trace = {
            "trace_id": trace_id,
            "timestamp": ts_str,
            "query": query,
            "prompt_version": "v1.2.0-system",
            "retrieved_chunks": retrieved_chunks,
            "model": "gpt-4o-mini",
            "model_params": {
                "temperature": 0.0,
                "max_tokens": 256
            },
            "raw_output": raw_output
        }
        traces.append(trace)

    with open(output_path, "w", encoding="utf-8") as f:
        for t in traces:
            f.write(json.dumps(t) + "\n")

    print(f"Successfully wrote {len(traces)} traces to {output_path}.")

if __name__ == "__main__":
    generate_traces()
