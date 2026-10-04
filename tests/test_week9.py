"""
Unit tests for Week 9 MCP Architecture:
Verifies:
  - Discovery before (3 tools) and after (6 tools)
  - Zero agent code changes
  - Actionable recoverable error handling
  - Bonus Gateway process fan-out and token-scoped denials
"""

import json
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import McpDocsAgent
from src.mcp.protocol import McpClientConnection
from src.mcp.docs_server import DocsSearchMcpServer
from src.mcp.registry_server import PackageRegistryMcpServer
from src.mcp.gateway import McpGateway


class TestWeek9Mcp(unittest.TestCase):
    def test_tool_discovery_before_and_after(self):
        # Server 1 only
        agent_s1 = McpDocsAgent("mcp_config_server1.json")
        summary_s1 = agent_s1.get_discovered_tools_summary()
        self.assertEqual(summary_s1["total_tools"], 3)
        self.assertIn("search_docs", summary_s1["tool_names"])
        self.assertIn("get_openapi_spec", summary_s1["tool_names"])
        self.assertIn("check_symbol_deprecation", summary_s1["tool_names"])

        # Server 1 + Server 2 (Config-only change)
        agent_s2 = McpDocsAgent("mcp_config.json")
        summary_s2 = agent_s2.get_discovered_tools_summary()
        self.assertEqual(summary_s2["total_tools"], 6)
        self.assertIn("get_package_versions", summary_s2["tool_names"])
        self.assertIn("get_deprecation_notice", summary_s2["tool_names"])
        self.assertIn("get_release_metadata", summary_s2["tool_names"])

    def test_query_provably_calls_registry_server(self):
        agent = McpDocsAgent("mcp_config.json")
        res = agent.run("Check package versions and deprecation notice for ai-sdk in registry")
        called_tools = [s["tool"] for s in res["trace"]]
        self.assertIn("get_package_versions", called_tools)
        self.assertIn("get_deprecation_notice", called_tools)

    def test_docstring_recoverable_error(self):
        docs_server = DocsSearchMcpServer(mode="new")
        client = McpClientConnection(docs_server)
        client.send("initialize")
        res = client.send("tools/call", {"name": "search_docs", "arguments": {"query": "Client", "version": "v4.0"}})
        self.assertTrue(res["result"]["isError"])
        err_text = res["result"]["content"][0]["text"]
        self.assertIn("latest published active version is 'v3.2'", err_text)
        self.assertIn("Actionable Recovery", err_text)

    def test_bonus_gateway_token_scoping_and_audit(self):
        gw = McpGateway(scoped_token="token-read-version-only")
        client = McpClientConnection(gw)
        client.send("initialize")

        # 1. Allowed call
        res_allowed = client.send("tools/call", {
            "name": "get_package_versions",
            "arguments": {"package": "ai-sdk"},
            "caller": "test-agent"
        })
        self.assertFalse(res_allowed["result"]["isError"])

        # 2. Denied call with recoverable error
        res_denied = client.send("tools/call", {
            "name": "get_deprecation_notice",
            "arguments": {"package": "ai-sdk", "version": "v2.0.0"},
            "caller": "test-agent"
        })
        self.assertTrue(res_denied["result"]["isError"])
        self.assertIn("Permission Denied", res_denied["result"]["content"][0]["text"])

        # 3. Single audit lines
        self.assertEqual(len(gw.audit_logs), 2)
        self.assertIn("status=ALLOWED", gw.audit_logs[0])
        self.assertIn("status=DENIED", gw.audit_logs[1])


if __name__ == "__main__":
    unittest.main()
