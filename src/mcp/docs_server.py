"""
Server 1: Docs Search MCP Server (Developer Documentation Server).
Exposes tools for searching markdown guides, OpenAPI endpoint schemas, and symbol deprecations.
Demonstrates Requirement 5: Docstring rewritten as a prompt with actionable, recoverable error paths.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.mcp.protocol import McpServerBase

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OPENAPI_SPECS_PATH = DATA_DIR / "openapi_specs.json"
DEPRECATIONS_PATH = DATA_DIR / "deprecations.json"


# Docstring Comparison for Requirement 5
OLD_SEARCH_DOCS_DOCSTRING = "Search prose documentation for keywords and concepts. Returns error if version directory is not found."

REWRITTEN_SEARCH_DOCS_PROMPT_DOCSTRING = (
    "Search developer documentation, migration guides, and code examples for SDK usage patterns. "
    "Call this tool whenever verifying endpoint changes or generating migration code. "
    "If a queried version does not exist, inspect the returned recovery guidance for the latest "
    "published active release (v3.2) and migration changelogs before generating code. "
    "Do not hallucinate methods for unreleased versions."
)


class DocsSearchMcpServer(McpServerBase):
    def __init__(self, mode: str = "new"):
        super().__init__(server_name="docs-search-server", version="1.2.0")
        self.mode = mode  # "old" (uninformative error) vs "new" (recoverable error)
        self._setup_tools()

    def _load_openapi_specs(self) -> Dict[str, Any]:
        if OPENAPI_SPECS_PATH.exists():
            with open(OPENAPI_SPECS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _load_deprecations(self) -> List[Dict[str, Any]]:
        if DEPRECATIONS_PATH.exists():
            with open(DEPRECATIONS_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("deprecations", [])
        return []

    def _setup_tools(self):
        docstring = REWRITTEN_SEARCH_DOCS_PROMPT_DOCSTRING if self.mode == "new" else OLD_SEARCH_DOCS_DOCSTRING

        # 1. search_docs
        self.register_tool(
            name="search_docs",
            description=docstring,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query keywords or method name"},
                    "version": {"type": "string", "description": "Target API version (e.g. 'v1', 'v2', 'v3', 'v4')"},
                },
                "required": ["query", "version"],
            },
            handler=self.search_docs,
        )

        # 2. get_openapi_spec
        self.register_tool(
            name="get_openapi_spec",
            description="Retrieve OpenAPI schema specification details including HTTP method, path, input parameters, and responses.",
            input_schema={
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string", "description": "API path or endpoint string e.g. /v3/client/send"},
                    "version": {"type": "string", "description": "API specification version e.g. 'v1', 'v2', 'v3'"},
                },
                "required": ["endpoint", "version"],
            },
            handler=self.get_openapi_spec,
        )

        # 3. check_symbol_deprecation
        self.register_tool(
            name="check_symbol_deprecation",
            description="Query SDK migration changelog and deprecation registry to check if a symbol has been deprecated and find replacements.",
            input_schema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Class method or API symbol name e.g. Client.send or Auth.login"},
                    "version": {"type": "string", "description": "Source API version"},
                },
                "required": ["symbol", "version"],
            },
            handler=self.check_symbol_deprecation,
        )

    def search_docs(self, query: str, version: str) -> Dict[str, Any]:
        clean_v = version.strip().lower()
        target_dir = DATA_DIR / clean_v

        # Unknown / unreleased version path (Demonstrates Requirement 5)
        if not target_dir.exists():
            if self.mode == "old":
                # Old uninformative error: model cannot recover
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error 3: Documentation directory not found for version '{version}'",
                        }
                    ],
                    "isError": True,
                }
            else:
                # New recoverable error: guides model to latest published version (v3.2)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"No documentation found for requested version '{version}'. "
                                f"The latest published active version is 'v3.2'. "
                                f"Deprecated methods and migration paths from v2 to v3 are documented under 'v3/migration' and 'v3/client_v3.txt'. "
                                f"Actionable Recovery: Please retry your query targeting version 'v3' or refer to 'v3.2' migration guides."
                            ),
                        }
                    ],
                    "isError": True,
                }

        # Search matching files
        matches = []
        tokens = [t.lower() for t in query.split() if len(t) > 2]
        for file_path in target_dir.glob("*.*"):
            if file_path.suffix in [".txt", ".md"]:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                content_lower = content.lower()
                score = sum(content_lower.count(t) for t in tokens)
                if score > 0 or any(p in file_path.name.lower() for p in tokens):
                    matches.append({
                        "file": file_path.name,
                        "snippet": content[:400].strip(),
                    })

        matches.sort(key=lambda x: len(x["snippet"]), reverse=True)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "status": "success",
                        "version": clean_v,
                        "query": query,
                        "count": len(matches),
                        "results": matches[:2],
                    }, indent=2),
                }
            ],
            "isError": False,
        }

    def get_openapi_spec(self, endpoint: str, version: str) -> Dict[str, Any]:
        clean_v = version.strip().lower()
        specs = self._load_openapi_specs().get(clean_v, {})
        clean_ep = endpoint.strip()

        if clean_ep in specs:
            return {
                "content": [{"type": "text", "text": json.dumps({"endpoint": clean_ep, "spec": specs[clean_ep]}, indent=2)}],
                "isError": False,
            }

        # Partial match
        for ep, data in specs.items():
            if clean_ep in ep or any(part in ep for part in clean_ep.split("/") if part):
                return {
                    "content": [{"type": "text", "text": json.dumps({"endpoint": ep, "spec": data}, indent=2)}],
                    "isError": False,
                }

        return {
            "content": [{"type": "text", "text": f"Endpoint '{clean_ep}' not found in {clean_v} OpenAPI specification."}],
            "isError": True,
        }

    def check_symbol_deprecation(self, symbol: str, version: str) -> Dict[str, Any]:
        clean_v = version.strip().lower()
        deprecations = self._load_deprecations()
        q_sym = symbol.strip().lower()
        found = []
        for d in deprecations:
            if q_sym in d.get("symbol", "").lower():
                found.append(d)

        return {
            "content": [{"type": "text", "text": json.dumps({"symbol": symbol, "found": found}, indent=2)}],
            "isError": False,
        }
