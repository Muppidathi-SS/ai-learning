"""
Model Context Protocol (MCP) JSON-RPC 2.0 Base Protocol Implementation.
Standardizes initialize, tools/list, and tools/call lifecycle across stdio/in-memory transports.
"""

from dataclasses import dataclass, field
import json
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class McpTool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Any]
    server_name: str = "default"


class McpServerBase:
    """Base class for an MCP Server implementing standard JSON-RPC 2.0 endpoints."""

    def __init__(self, server_name: str, version: str = "1.0.0"):
        self.server_name = server_name
        self.version = version
        self.tools: Dict[str, McpTool] = {}
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.initialized: bool = False

    def register_tool(self, name: str, description: str, input_schema: Dict[str, Any], handler: Callable[..., Any]):
        self.tools[name] = McpTool(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler,
            server_name=self.server_name,
        )

    def register_resource(self, uri: str, name: str, mime_type: str, content: str):
        self.resources[uri] = {
            "uri": uri,
            "name": name,
            "mimeType": mime_type,
            "text": content,
        }

    def handle_request(self, request_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processes a JSON-RPC 2.0 message and returns the response dictionary."""
        jsonrpc = request_json.get("jsonrpc", "2.0")
        msg_id = request_json.get("id")
        method = request_json.get("method")
        params = request_json.get("params", {})

        # Handle notifications (no id)
        if msg_id is None:
            if method == "notifications/initialized":
                self.initialized = True
            return None

        # 1. initialize
        if method == "initialize":
            self.initialized = True
            return {
                "jsonrpc": jsonrpc,
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                    },
                    "serverInfo": {
                        "name": self.server_name,
                        "version": self.version,
                    },
                },
            }

        # 2. tools/list
        if method == "tools/list":
            tools_list = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                }
                for tool in self.tools.values()
            ]
            return {
                "jsonrpc": jsonrpc,
                "id": msg_id,
                "result": {
                    "tools": tools_list,
                },
            }

        # 3. tools/call
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in self.tools:
                return {
                    "jsonrpc": jsonrpc,
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method/Tool '{tool_name}' not found on server '{self.server_name}'",
                    },
                }

            tool = self.tools[tool_name]
            try:
                raw_result = tool.handler(**arguments)
                # Format standard MCP tool call result
                if isinstance(raw_result, dict) and "content" in raw_result:
                    return {
                        "jsonrpc": jsonrpc,
                        "id": msg_id,
                        "result": raw_result,
                    }
                else:
                    return {
                        "jsonrpc": jsonrpc,
                        "id": msg_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(raw_result, indent=2) if isinstance(raw_result, (dict, list)) else str(raw_result),
                                }
                            ],
                            "isError": False,
                        },
                    }
            except Exception as e:
                return {
                    "jsonrpc": jsonrpc,
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Tool execution failed: {str(e)}",
                            }
                        ],
                        "isError": True,
                    },
                }

        # 4. resources/list
        if method == "resources/list":
            return {
                "jsonrpc": jsonrpc,
                "id": msg_id,
                "result": {
                    "resources": list(self.resources.values()),
                },
            }

        # Default: Method not found
        return {
            "jsonrpc": jsonrpc,
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Unhandled method '{method}'",
            },
        }


class McpClientConnection:
    """Client connection for sending JSON-RPC 2.0 messages to an MCP server and recording wire traffic."""

    def __init__(self, server: McpServerBase):
        self.server = server
        self.msg_counter = 0
        self.wire_log: List[Dict[str, Any]] = []

    def send(self, method: str, params: Optional[Dict[str, Any]] = None, is_notification: bool = False) -> Optional[Dict[str, Any]]:
        self.msg_counter += 1
        req: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if not is_notification:
            req["id"] = self.msg_counter
        if params is not None:
            req["params"] = params

        res = self.server.handle_request(req)

        self.wire_log.append({
            "request": req,
            "response": res,
        })
        return res
