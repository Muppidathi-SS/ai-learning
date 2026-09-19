"""
Tools module for Developer Documentation and Migration Assistant.
Provides strictly non-overlapping tools for docs search, OpenAPI spec retrieval, and deprecation checks.
"""

from enum import Enum
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class ApiVersion(str, Enum):
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"

    @classmethod
    def from_str(cls, val: Any) -> "ApiVersion":
        if isinstance(val, cls):
            return val
        if isinstance(val, str):
            clean = val.strip().lower()
            for member in cls:
                if member.value == clean or member.name.lower() == clean:
                    return member
        raise ValueError(f"Invalid ApiVersion: {val}. Must be one of {[m.value for m in cls]}")


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OPENAPI_SPECS_PATH = DATA_DIR / "openapi_specs.json"
DEPRECATIONS_PATH = DATA_DIR / "deprecations.json"


def _load_openapi_specs() -> Dict[str, Any]:
    if OPENAPI_SPECS_PATH.exists():
        with open(OPENAPI_SPECS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_deprecations() -> List[Dict[str, Any]]:
    if DEPRECATIONS_PATH.exists():
        with open(DEPRECATIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("deprecations", [])
    return []


def search_docs(query: str, version: ApiVersion) -> Dict[str, Any]:
    """
    Search prose documentation, developer guides, and markdown code examples for tutorials, concepts, and usage patterns.
    """
    version_enum = ApiVersion.from_str(version)
    target_dir = DATA_DIR / version_enum.value

    if not target_dir.exists():
        return {
            "status": "error",
            "message": f"Documentation directory not found for version {version_enum.value}",
            "results": [],
        }

    matches = []
    tokens = [t.lower() for t in query.split() if len(t) > 2]

    for file_path in target_dir.glob("*.*"):
        if file_path.suffix in [".txt", ".md"]:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            content_lower = content.lower()
            score = sum(content_lower.count(token) for token in tokens)
            if score > 0 or any(part in file_path.name.lower() for part in tokens):
                matches.append({
                    "file": file_path.name,
                    "score": score,
                    "content_snippet": content[:500].strip(),
                    "full_content": content,
                })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return {
        "status": "success",
        "tool": "search_docs",
        "version": version_enum.value,
        "query": query,
        "count": len(matches),
        "results": matches[:3],
    }


def get_openapi_spec(endpoint: str, version: ApiVersion) -> Dict[str, Any]:
    """
    Retrieve OpenAPI schema specification details including HTTP method, path, input parameters, data types, and status responses.
    """
    version_enum = ApiVersion.from_str(version)
    specs = _load_openapi_specs().get(version_enum.value, {})

    clean_endpoint = endpoint.strip()
    if clean_endpoint in specs:
        return {
            "status": "success",
            "tool": "get_openapi_spec",
            "version": version_enum.value,
            "endpoint": clean_endpoint,
            "spec": specs[clean_endpoint],
        }

    # Fallback partial match
    for ep, data in specs.items():
        if clean_endpoint in ep or any(part in ep for part in clean_endpoint.split("/") if part):
            return {
                "status": "success",
                "tool": "get_openapi_spec",
                "version": version_enum.value,
                "endpoint": ep,
                "spec": data,
            }

    return {
        "status": "not_found",
        "tool": "get_openapi_spec",
        "version": version_enum.value,
        "endpoint": clean_endpoint,
        "message": f"Endpoint '{clean_endpoint}' not found in {version_enum.value} OpenAPI specs.",
    }


def check_deprecation(symbol_or_endpoint: str, version: ApiVersion) -> Dict[str, Any]:
    """
    Query migration changelog and deprecation registry to check if an API symbol or endpoint has been deprecated, and retrieve replacement names.
    """
    version_enum = ApiVersion.from_str(version)
    deprecations = _load_deprecations()

    query_str = symbol_or_endpoint.strip().lower()
    found = []

    for dep in deprecations:
        dep_sym = dep.get("symbol", "").lower()
        dep_ver = dep.get("version", "").lower()
        if (query_str in dep_sym or dep_sym in query_str) and (dep_ver == version_enum.value or dep_ver <= version_enum.value):
            found.append(dep)

    if found:
        return {
            "status": "deprecated_found",
            "tool": "check_deprecation",
            "version": version_enum.value,
            "query": symbol_or_endpoint,
            "count": len(found),
            "deprecations": found,
        }

    return {
        "status": "none_found",
        "tool": "check_deprecation",
        "version": version_enum.value,
        "query": symbol_or_endpoint,
        "deprecations": [],
        "message": f"No active deprecations registered for '{symbol_or_endpoint}' up to version {version_enum.value}.",
    }


# Standard tool registration registry
AVAILABLE_TOOLS = {
    "search_docs": search_docs,
    "get_openapi_spec": get_openapi_spec,
    "check_deprecation": check_deprecation,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Search prose documentation, developer guides, and markdown code examples for tutorials, concepts, and usage patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keywords or phrase to search documentation for"},
                    "version": {"type": "string", "enum": ["v1", "v2", "v3"], "description": "Target API version"},
                },
                "required": ["query", "version"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_openapi_spec",
            "description": "Retrieve OpenAPI schema specification details including HTTP method, path, input parameters, data types, and status responses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string", "description": "API path or endpoint string e.g. /v3/client/send"},
                    "version": {"type": "string", "enum": ["v1", "v2", "v3"], "description": "API specification version"},
                },
                "required": ["endpoint", "version"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_deprecation",
            "description": "Query migration changelog and deprecation registry to check if an API symbol or endpoint has been deprecated, and retrieve replacement names.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol_or_endpoint": {"type": "string", "description": "Class method or API endpoint name to inspect"},
                    "version": {"type": "string", "enum": ["v1", "v2", "v3"], "description": "Current source API version"},
                },
                "required": ["symbol_or_endpoint", "version"],
            },
        },
    },
]
