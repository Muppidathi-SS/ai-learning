"""
Server 2: Package Registry MCP Server (DevRel Server).
Exposes tools for querying package version metadata, release dates, and deprecation notices.
Bolted on via MCP configuration without modifying the agent code.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.mcp.protocol import McpServerBase

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = PROJECT_ROOT / "data" / "package_registry.json"


class PackageRegistryMcpServer(McpServerBase):
    def __init__(self):
        super().__init__(server_name="package-registry-server", version="2.1.0")
        self._setup_tools()

    def _load_registry(self) -> Dict[str, Any]:
        if REGISTRY_PATH.exists():
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("packages", {})
        return {}

    def _setup_tools(self):
        # 1. get_package_versions
        self.register_tool(
            name="get_package_versions",
            description="Retrieve all published release versions, release dates, and current latest stable version for a package from the registry.",
            input_schema={
                "type": "object",
                "properties": {
                    "package": {"type": "string", "description": "Package identifier e.g. 'ai-sdk'"},
                },
                "required": ["package"],
            },
            handler=self.get_package_versions,
        )

        # 2. get_deprecation_notice
        self.register_tool(
            name="get_deprecation_notice",
            description="Query package registry deprecation notices, sunset dates, and replacement packages for a specified package and version.",
            input_schema={
                "type": "object",
                "properties": {
                    "package": {"type": "string", "description": "Package identifier e.g. 'ai-sdk'"},
                    "version": {"type": "string", "description": "Package version string e.g. 'v1.0.0', 'v2.0.0'"},
                },
                "required": ["package", "version"],
            },
            handler=self.get_deprecation_notice,
        )

        # 3. get_release_metadata
        self.register_tool(
            name="get_release_metadata",
            description="Fetch package release metadata including maintainer, license, release timestamp, and repository URL.",
            input_schema={
                "type": "object",
                "properties": {
                    "package": {"type": "string", "description": "Package name"},
                },
                "required": ["package"],
            },
            handler=self.get_release_metadata,
        )

    def get_package_versions(self, package: str) -> Dict[str, Any]:
        registry = self._load_registry()
        pkg_data = registry.get(package)
        if not pkg_data:
            return {
                "content": [{"type": "text", "text": f"Package '{package}' not found in registry."}],
                "isError": True,
            }

        versions_summary = [
            {
                "version": v["version"],
                "release_date": v["release_date"],
                "status": v["status"],
                "is_deprecated": v["is_deprecated"],
            }
            for v in pkg_data.get("versions", [])
        ]

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "package": package,
                        "latest_version": pkg_data.get("latest_version"),
                        "total_releases": len(versions_summary),
                        "versions": versions_summary,
                    }, indent=2),
                }
            ],
            "isError": False,
        }

    def get_deprecation_notice(self, package: str, version: str) -> Dict[str, Any]:
        registry = self._load_registry()
        pkg_data = registry.get(package)
        if not pkg_data:
            return {
                "content": [{"type": "text", "text": f"Package '{package}' not found in registry."}],
                "isError": True,
            }

        clean_v = version.strip().lower()
        matched_v = None
        for v in pkg_data.get("versions", []):
            if v["version"].lower() == clean_v or clean_v in v["version"].lower():
                matched_v = v
                break

        if not matched_v:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Version '{version}' not found for package '{package}'. Available: {[v['version'] for v in pkg_data.get('versions', [])]}",
                    }
                ],
                "isError": True,
            }

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "package": package,
                        "version": matched_v["version"],
                        "status": matched_v["status"],
                        "is_deprecated": matched_v["is_deprecated"],
                        "deprecation_notice": matched_v.get("deprecation_notice") or "No active deprecation notice. Version is supported.",
                        "recommended_upgrade": pkg_data.get("latest_version"),
                    }, indent=2),
                }
            ],
            "isError": False,
        }

    def get_release_metadata(self, package: str) -> Dict[str, Any]:
        registry = self._load_registry()
        pkg_data = registry.get(package)
        if not pkg_data:
            return {
                "content": [{"type": "text", "text": f"Package '{package}' not found in registry."}],
                "isError": True,
            }

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "package": package,
                        "maintainer": pkg_data.get("maintainer"),
                        "license": pkg_data.get("license"),
                        "repository": pkg_data.get("repository"),
                        "latest_version": pkg_data.get("latest_version"),
                    }, indent=2),
                }
            ],
            "isError": False,
        }
