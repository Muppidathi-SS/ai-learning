"""
Bonus Challenge: MCP Gateway Process (Single Front Door with Fan-out, Single-line Audit Logging, and Scoped Tokens).
Fans out tools/list and tools/call to downstream servers (docs-server and package-registry).
Writes single audit line: '[AUDIT] caller=<caller> | tool=<tool> | target=<pkg>@<ver> | status=<status>'
Enforces capability tokens with recoverable error responses on denied scopes.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.mcp.protocol import McpServerBase
from src.mcp.docs_server import DocsSearchMcpServer
from src.mcp.registry_server import PackageRegistryMcpServer

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GATEWAY_LOG_PATH = PROJECT_ROOT / "gateway_audit.log"


class McpGateway(McpServerBase):
    def __init__(self, scoped_token: Optional[str] = None):
        super().__init__(server_name="mcp-gateway-frontdoor", version="1.0.0")
        self.scoped_token = scoped_token  # e.g. "token-read-version-only" vs "token-full-access"
        self.docs_server = DocsSearchMcpServer()
        self.registry_server = PackageRegistryMcpServer()
        self.downstream_servers = {
            "docs": self.docs_server,
            "registry": self.registry_server,
        }
        self.audit_logs: List[str] = []
        self._aggregate_tools()

    def _aggregate_tools(self):
        """Discovers tools across all downstream servers and registers them at the single front door."""
        self.tools.clear()
        for srv in self.downstream_servers.values():
            for name, tool in srv.tools.items():
                self.tools[name] = tool

    def set_token(self, token: Optional[str]):
        self.scoped_token = token

    def _log_audit(self, caller: str, tool_name: str, target: str, status: str):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        log_line = f"[{timestamp}] [AUDIT] caller={caller} | tool={tool_name} | target={target} | status={status}"
        self.audit_logs.append(log_line)
        try:
            with open(GATEWAY_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception:
            pass

    def handle_request(self, request_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = request_json.get("method")
        msg_id = request_json.get("id")
        params = request_json.get("params", {})

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            caller = params.get("caller", "docs-assistant")

            # Extract target package@version
            pkg = arguments.get("package") or arguments.get("symbol") or "ai-sdk"
            ver = arguments.get("version") or "v3"
            target_str = f"{pkg}@{ver}"

            # Token Scope Enforcement (Bonus Challenge)
            if self.scoped_token == "token-read-version-only":
                # Specifically deny get_deprecation_notice under restricted token scope
                if tool_name == "get_deprecation_notice":
                    status = "DENIED (Insufficient scope: requires 'read:deprecations')"
                    self._log_audit(caller, tool_name, target_str, status)
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Permission Denied: Scoped token 'token-read-version-only' is missing capability 'read:deprecations'. "
                                        "Actionable Recovery: Use 'get_package_versions' to inspect release timestamps and active status, "
                                        "or contact security-ops@internal.company.net for elevated deprecation scope."
                                    ),
                                }
                            ],
                            "isError": True,
                        },
                    }

            # If authorized, log ALLOWED and route to downstream server
            status = "ALLOWED"
            self._log_audit(caller, tool_name, target_str, status)

            # Route to appropriate server
            for srv in self.downstream_servers.values():
                if tool_name in srv.tools:
                    return srv.handle_request(request_json)

        # For initialize and tools/list, handle normally
        return super().handle_request(request_json)
