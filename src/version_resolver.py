"""
src/version_resolver.py
========================
Resolves the caller's actual SDK version BEFORE retrieval and answering.

Requirements:
- Determines caller's target version: e.g. "v2.4", "v2.x", "2.4" -> Normalized "v2", Detailed "v2.4"
- Checks question phrasing for explicit version statements ("In SDK 2.4...", "we are on v2.x", "v3.0")
- Uses declared caller context if question text is version-neutral
- Prevents version cross-contamination before any search or LLM generation occurs
"""

import re
from typing import Any, Dict, Optional, Tuple


class VersionResolver:
    """
    Resolves caller SDK version deterministically before retrieval.
    """

    @staticmethod
    def resolve(query: str, caller_context: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
        """
        Resolves caller version into (normalized_version, detailed_version).
        Normalized version: 'v2' or 'v3' (used for hard metadata filtering).
        Detailed version: 'v2.4', 'v3.0', etc.
        """
        caller_ctx = caller_context or {}
        explicit_ver = caller_ctx.get("caller_version") or caller_ctx.get("target_version")
        
        q_lower = query.lower()

        # 1. Check explicit caller context first
        if explicit_ver:
            norm_ctx = VersionResolver._normalize(str(explicit_ver))
            if norm_ctx:
                return norm_ctx

        # 2. Extract from query text
        # Look for patterns like "v2.4", "2.4", "v3.0", "sdk 2", "sdk v3", "version 2.x"
        v3_match = re.search(r"\b(v3(?:\.\d+)?|3\.\d+|sdk\s+3|version\s+3)\b", q_lower)
        v2_match = re.search(r"\b(v2(?:\.\d+)?|2\.\d+|sdk\s+2|version\s+2)\b", q_lower)

        if v2_match and not v3_match:
            detail = v2_match.group(1).replace("sdk ", "v").replace("version ", "v")
            if not detail.startswith("v"):
                detail = f"v{detail}"
            return "v2", detail

        if v3_match and not v2_match:
            detail = v3_match.group(1).replace("sdk ", "v").replace("version ", "v")
            if not detail.startswith("v"):
                detail = f"v{detail}"
            return "v3", detail

        # If both are mentioned (e.g. migration queries "from v2 to v3"), the target is v3 (migration destination)
        if v2_match and v3_match:
            if "migrate" in q_lower or "upgrade" in q_lower or "to v3" in q_lower or "to 3" in q_lower:
                return "v3", "v3.0"
            return "v2", "v2.4"

        # 3. Default fallback based on fleet telemetry (default to v2 if unspecified, or caller declared environment)
        fallback = caller_ctx.get("default_version", "v2.4")
        return VersionResolver._normalize(fallback)

    @staticmethod
    def _normalize(ver_str: str) -> Tuple[str, str]:
        clean = ver_str.strip().lower()
        if "3" in clean:
            detail = clean if clean.startswith("v") else f"v{clean}"
            return "v3", detail
        detail = clean if clean.startswith("v") else f"v{clean}"
        return "v2", detail
