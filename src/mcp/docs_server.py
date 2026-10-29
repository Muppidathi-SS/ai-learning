"""
src/mcp/docs_server.py
======================
MCP Server exposing genuine SDK capabilities:
1. version_scoped_doc_search: Searches markdown docs scoped strictly to caller's version.
2. changelog_deprecation_lookup: Looks up deprecation notices and removal versions.
3. symbol_exists_check: Performs AST/symbol-table verification against target version.

Discovered at runtime by the agent via standard JSON-RPC 2.0 initialize -> tools/list.
Can be invoked live by external clients (e.g. Thursday's fresh-eyes reviewer).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.mcp.protocol import McpServerBase
from src.retriever import VersionScopedRetriever
from src.symbol_validator import SymbolTableValidator

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DEPRECATIONS_PATH = DATA_DIR / "deprecations.json"


class SdkDocsMcpServer(McpServerBase):
    """
    Standard MCP Server for SDK Documentation, Deprecation Registry, and Symbol Validation.
    """

    def __init__(self):
        super().__init__(server_name="sdk-docs-server", version="2.0.0")
        self.retriever = VersionScopedRetriever()
        self.symbol_validator = SymbolTableValidator()
        self.deprecations = self._load_deprecations()
        self._setup_tools()

    def _load_deprecations(self) -> List[Dict[str, Any]]:
        if DEPRECATIONS_PATH.exists():
            with open(DEPRECATIONS_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("deprecations", [])
        return []

    def _setup_tools(self):
        # Tool 1: version_scoped_doc_search
        self.register_tool(
            name="version_scoped_doc_search",
            description=(
                "Search SDK prose documentation and markdown guides strictly filtered by the caller's target version. "
                "Returns version-tagged clickable citations and matching content snippets."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keywords or method name to search"},
                    "version": {"type": "string", "description": "Target SDK version (e.g. 'v2', 'v2.4', 'v3', 'v3.0')"},
                },
                "required": ["query", "version"],
            },
            handler=self.version_scoped_doc_search,
        )

        # Tool 2: changelog_deprecation_lookup
        self.register_tool(
            name="changelog_deprecation_lookup",
            description=(
                "Query migration changelog and deprecation registry to check if an API symbol has been deprecated "
                "or removed in a future version. Returns replacement symbol and sunset version."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Class or method name e.g. 'Client.query' or 'Stream.feed'"},
                    "current_version": {"type": "string", "description": "Current SDK version the caller is using"},
                },
                "required": ["symbol"],
            },
            handler=self.changelog_deprecation_lookup,
        )

        # Tool 3: symbol_exists_check
        self.register_tool(
            name="symbol_exists_check",
            description=(
                "Check whether a class or method exists in the symbol table for a specific SDK version. "
                "Returns boolean exists, parameters, and mandatory rules (e.g. timeout in v3.0 Client.search)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Fully-qualified symbol name e.g. 'Client.query' or 'Client.search'"},
                    "version": {"type": "string", "description": "SDK version to check against e.g. 'v2' or 'v3'"},
                },
                "required": ["symbol", "version"],
            },
            handler=self.symbol_exists_check,
        )

    def version_scoped_doc_search(self, query: str, version: str) -> Dict[str, Any]:
        results = self.retriever.search(query, target_version=version, top_k=3)
        return {
            "query": query,
            "version": version,
            "count": len(results),
            "results": [
                {
                    "file": r["file"],
                    "version_label": r["version_label"],
                    "citation": r["citation"],
                    "snippet": r["content"][:400].strip(),
                }
                for r in results
            ],
        }

    def changelog_deprecation_lookup(self, symbol: str, current_version: str = "v2") -> Dict[str, Any]:
        sym_clean = symbol.strip().lower()
        matched = []
        for dep in self.deprecations:
            d_sym = dep.get("symbol", "").lower()
            if sym_clean in d_sym or d_sym in sym_clean:
                matched.append(dep)

        if matched:
            return {
                "status": "deprecation_found",
                "symbol": symbol,
                "current_version": current_version,
                "deprecations": matched,
            }
        return {
            "status": "active_symbol",
            "symbol": symbol,
            "current_version": current_version,
            "message": f"No deprecation notices found for '{symbol}'.",
        }

    def symbol_exists_check(self, symbol: str, version: str) -> Dict[str, Any]:
        norm_v = "v3" if "3" in version else "v2"
        v_table = self.symbol_validator.symbol_table.get(norm_v, {}).get("classes", {})

        parts = symbol.strip().split(".")
        class_name = parts[0]
        method_name = parts[1] if len(parts) > 1 else None

        if class_name not in v_table:
            return {
                "symbol": symbol,
                "version": norm_v,
                "exists": False,
                "reason": f"Class '{class_name}' does not exist in SDK {norm_v}.",
            }

        if method_name:
            methods = v_table[class_name].get("methods", {})
            if method_name not in methods:
                # Check if it was removed in v3
                if norm_v == "v3" and method_name in ["query", "feed", "dispatch", "login", "get_config", "subscribe"]:
                    return {
                        "symbol": symbol,
                        "version": norm_v,
                        "exists": False,
                        "removed_in_v3": True,
                        "reason": f"Method '{symbol}' no longer exists in {norm_v}. It was removed in v3.0.",
                    }
                return {
                    "symbol": symbol,
                    "version": norm_v,
                    "exists": False,
                    "reason": f"Method '{method_name}' does not exist in {class_name} for SDK {norm_v}.",
                }

            spec = methods[method_name]
            return {
                "symbol": symbol,
                "version": norm_v,
                "exists": True,
                "parameters": spec.get("parameters", []),
                "required": spec.get("required", []),
                "notes": spec.get("notes", ""),
                "deprecated_in": spec.get("deprecated_in"),
                "removed_in": spec.get("removed_in"),
                "migration": spec.get("migration"),
            }

        return {
            "symbol": symbol,
            "version": norm_v,
            "exists": True,
            "methods": list(v_table[class_name].get("methods", {}).keys()),
        }


# Backwards compatibility export
DocsSearchMcpServer = SdkDocsMcpServer
