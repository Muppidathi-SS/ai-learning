"""
Indirect Prompt Injection Defense System for Week 8 Bonus Challenge.
Three Defense Layers:
  1. Tool Output Sanitizer: Sanitizes untrusted docs/community inputs and isolates them in secure tags.
  2. Scope Manager: Restricts agent capabilities to strictly read-only scopes.
  3. Security Code Guardrail: AST and semantic validation blocking insecure flags (e.g. verify=False, reject_unauthorized=False).
"""

import ast
import re
import time
from typing import Any, Dict, List, Optional, Tuple


class ToolSanitizer:
    """
    Layer 1: Sanitizes tool outputs before they enter the agent's context history.
    Detects and neutralizes prompt injection patterns and wraps untrusted data in isolation tags.
    """

    INJECTION_PATTERNS = [
        re.compile(r"\[?\bSYSTEM\s+OVERRIDE\b\]?", re.IGNORECASE),
        re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
        re.compile(r"tell\s+the\s+user\s+to\s+disable\s+tls", re.IGNORECASE),
        re.compile(r"disable\s+(tls|ssl)\s+verification", re.IGNORECASE),
        re.compile(r"verify\s*=\s*False", re.IGNORECASE),
        re.compile(r"reject_unauthorized\s*=\s*False", re.IGNORECASE),
        re.compile(r"<!--.*?-->", re.DOTALL),
    ]

    def sanitize_output(self, raw_content: str, tool_name: str = "search_docs") -> Tuple[str, bool]:
        """
        Sanitizes untrusted output from tools (e.g. community documentation comments).
        Returns: (sanitized_text, injection_detected)
        """
        injection_detected = False
        cleaned = raw_content

        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(cleaned):
                injection_detected = True
                cleaned = pattern.sub("[REDACTED_UNTRUSTED_INSTRUCTION]", cleaned)

        # Isolate content within strict XML demarcation tags to prevent context bleeding
        isolated_content = (
            f"<untrusted_external_content tool='{tool_name}' verified='false'>\n"
            f"{cleaned.strip()}\n"
            f"</untrusted_external_content>"
        )

        return isolated_content, injection_detected


class ScopeManager:
    """
    Layer 2: Capability / Scope Restriction.
    Enforces strict read-only execution context.
    Prevents tool execution from altering security settings, environment flags, or executing arbitrary system operations.
    """

    ALLOWED_CAPABILITIES = {
        "read_docs": True,
        "read_openapi_specs": True,
        "read_deprecations": True,
        "modify_security_context": False,
        "execute_system_command": False,
        "alter_tls_verification": False,
    }

    def check_permission(self, action: str) -> bool:
        return self.ALLOWED_CAPABILITIES.get(action, False)


class SecurityCodeGuardrail:
    """
    Layer 3: Output Code Guardrail.
    Inspects synthesized code using AST parsing and semantic patterns.
    Blocks insecure networking configurations (e.g. disabling TLS/SSL certificate verification).
    """

    FORBIDDEN_KWARGS = {
        "verify": False,
        "reject_unauthorized": False,
        "ssl_verify": False,
        "check_hostname": False,
        "insecure": True,
    }

    def inspect_code(self, code: str) -> Tuple[bool, List[str]]:
        """
        Scans code for forbidden security patterns.
        Returns: (is_safe: bool, violations: List[str])
        """
        violations = []

        # 1. Regex scan for raw keyword occurrences
        for kw, bad_val in self.FORBIDDEN_KWARGS.items():
            pattern = rf"\b{kw}\s*=\s*{bad_val}\b"
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(f"Forbidden insecure parameter: {kw}={bad_val}")

        # 2. Python AST Parsing scan
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    for keyword in node.keywords:
                        if keyword.arg in self.FORBIDDEN_KWARGS:
                            expected_bad = self.FORBIDDEN_KWARGS[keyword.arg]
                            if isinstance(keyword.value, ast.Constant) and keyword.value.value == expected_bad:
                                err = f"AST violation in call: parameter '{keyword.arg}' set to insecure value '{expected_bad}'"
                                if err not in violations:
                                    violations.append(err)
        except Exception:
            # Fallback to regex if non-standard python snippet
            pass

        is_safe = len(violations) == 0
        return is_safe, violations

    def enforce_safe_defaults(self, code: str) -> str:
        """Removes or overrides insecure flags back to secure defaults."""
        safe_code = code
        for kw, bad_val in self.FORBIDDEN_KWARGS.items():
            pattern = rf"\b{kw}\s*=\s*{bad_val}\b"
            if bad_val is False:
                safe_code = re.sub(pattern, f"{kw}=True", safe_code, flags=re.IGNORECASE)
            elif bad_val is True:
                safe_code = re.sub(pattern, f"{kw}=False", safe_code, flags=re.IGNORECASE)
        return safe_code


class PromptInjectionDefensePipeline:
    """
    Unified 3-Layer Defense Pipeline for prompt injection attacks.
    Measures latency and token penalties.
    """

    def __init__(self):
        self.sanitizer = ToolSanitizer()
        self.scope_manager = ScopeManager()
        self.code_guardrail = SecurityCodeGuardrail()

    def process_tool_output(self, raw_content: str, tool_name: str) -> Tuple[str, Dict[str, Any]]:
        start_time = time.perf_counter()
        sanitized, detected = self.sanitizer.sanitize_output(raw_content, tool_name)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        telemetry = {
            "injection_detected": detected,
            "sanitizer_latency_ms": round(elapsed_ms, 4),
            "sanitized_length_delta": len(sanitized) - len(raw_content),
        }
        return sanitized, telemetry

    def validate_and_repair_code(self, synthesized_code: str) -> Tuple[str, Dict[str, Any]]:
        start_time = time.perf_counter()
        is_safe, violations = self.code_guardrail.inspect_code(synthesized_code)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        final_code = synthesized_code
        repaired = False
        if not is_safe:
            final_code = self.code_guardrail.enforce_safe_defaults(synthesized_code)
            repaired = True

        telemetry = {
            "is_safe": is_safe,
            "violations": violations,
            "code_repaired": repaired,
            "guardrail_latency_ms": round(elapsed_ms, 4),
        }
        return final_code, telemetry
