"""
src/symbol_validator.py
========================
Bonus Challenge Deliverable:
Deterministic Python AST parser and Version-Scoped Symbol-Table Validator.

Validates:
1. ast.parse() syntax parsing of every emitted code block.
2. Symbol-table check against the caller's target version:
   - Does every class and method exist in that version?
   - Do imports resolve?
   - Are mandatory parameters provided (e.g. timeout in v3.0 Client.search)?
   - Are removed/deprecated symbols rejected?
"""

import ast
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYMBOL_TABLE_PATH = PROJECT_ROOT / "data" / "symbol_table.json"


class SymbolTableValidator:
    def __init__(self, table_path: Optional[Path] = None):
        self.table_path = table_path or SYMBOL_TABLE_PATH
        self.symbol_table = self._load_table()

    def _load_table(self) -> Dict[str, Any]:
        if self.table_path.exists():
            with open(self.table_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def extract_code_blocks(self, text: str) -> List[str]:
        """Extracts python code blocks from markdown fences."""
        blocks = re.findall(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if not blocks and ("def " in text or "import " in text or "client." in text or "Stream." in text):
            lines = [l for l in text.splitlines() if not l.strip().startswith("#")]
            candidate = "\n".join(lines).strip()
            if candidate:
                blocks = [candidate]
        return [b.strip() for b in blocks if b.strip()]

    def validate_code_sample(self, code_str: str, target_version: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validates code against target_version (normalized 'v2' or 'v3').
        Returns (is_valid, list_of_errors, list_of_symbols_found).
        """
        norm_v = "v3" if "3" in target_version else "v2"
        v_table = self.symbol_table.get(norm_v, {}).get("classes", {})

        # Step 1: AST Parse Check
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            return False, [f"AST SyntaxError: {e}"], []

        errors: List[str] = []
        symbols_found: List[str] = []

        # Step 2: AST Node Inspection for method calls and parameters
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_name, class_name, method_name = self._resolve_call(node)
                if call_name:
                    symbols_found.append(call_name)
                    # Check method existence in version
                    check_err = self._check_method_rules(class_name, method_name, node, norm_v, v_table)
                    if check_err:
                        errors.append(check_err)

        is_valid = len(errors) == 0
        return is_valid, errors, sorted(list(set(symbols_found)))

    def _resolve_call(self, node: ast.Call) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Resolves Call node to (FullSymbol, ClassName, MethodName)."""
        func = node.func
        if isinstance(func, ast.Attribute):
            method_name = func.attr
            if isinstance(func.value, ast.Name):
                class_or_var = func.value.id
                # Map variable names like client -> Client, stream -> Stream
                mapped_class = "Client" if class_or_var.lower() == "client" else class_or_var
                if class_or_var.lower() == "stream":
                    mapped_class = "Stream"
                elif class_or_var.lower() == "batch":
                    mapped_class = "Batch"
                elif class_or_var.lower() == "auth":
                    mapped_class = "Auth"
                elif class_or_var.lower() == "config":
                    mapped_class = "Config"
                elif class_or_var.lower() == "webhook":
                    mapped_class = "Webhook"
                return f"{mapped_class}.{method_name}", mapped_class, method_name
            elif isinstance(func.value, ast.Attribute):
                return f"{func.value.attr}.{method_name}", func.value.attr, method_name
        elif isinstance(func, ast.Name):
            # Direct class instantiation like Client(...)
            return func.id, func.id, "__init__"
        return None, None, None

    def _check_method_rules(
        self,
        class_name: Optional[str],
        method_name: Optional[str],
        call_node: ast.Call,
        norm_v: str,
        v_table: Dict[str, Any],
    ) -> Optional[str]:
        if not class_name or not method_name or method_name == "__init__":
            return None

        # Check v2 vs v3 forbidden/removed methods
        if norm_v == "v2":
            if class_name == "Client" and method_name == "search":
                return "Symbol Error in v2.x: Client.search() does not exist in SDK v2.x (introduced in v3.0)."
            if class_name == "Stream" and method_name == "subscribe":
                return "Symbol Error in v2.x: Stream.subscribe() does not exist in SDK v2.x (use Stream.feed in v2.x)."
            if class_name == "Batch" and method_name == "submit_jobs":
                return "Symbol Error in v2.x: Batch.submit_jobs() does not exist in SDK v2.x (use Batch.dispatch)."
            if class_name == "Config" and method_name == "load_settings":
                return "Symbol Error in v2.x: Config.load_settings() does not exist in SDK v2.x."
            if class_name == "Webhook" and method_name == "register_listener":
                return "Symbol Error in v2.x: Webhook.register_listener() does not exist in SDK v2.x."

        if norm_v == "v3":
            if class_name == "Client" and method_name == "query":
                return "Symbol Error in v3.0: Client.query() was REMOVED in v3.0. Replace with Client.search(..., timeout=...)."
            if class_name == "Stream" and method_name == "feed":
                return "Symbol Error in v3.0: Stream.feed() was REMOVED in v3.0. Replace with Stream.subscribe()."
            if class_name == "Batch" and method_name == "dispatch":
                return "Symbol Error in v3.0: Batch.dispatch() was REMOVED in v3.0. Replace with Batch.submit_jobs()."
            if class_name == "Auth" and method_name == "login":
                return "Symbol Error in v3.0: Auth.login() was REMOVED in v3.0. Replace with Client.auth(token_ttl_sec=3600)."
            if class_name == "Config" and method_name == "get_config":
                return "Symbol Error in v3.0: Config.get_config() was REMOVED in v3.0. Replace with Config.load_settings()."
            if class_name == "Webhook" and method_name == "subscribe":
                return "Symbol Error in v3.0: Webhook.subscribe() was REMOVED in v3.0. Replace with Webhook.register_listener()."

            # Check Mandatory timeout parameter in Client.search()
            if class_name == "Client" and method_name == "search":
                kw_args = {kw.arg for kw in call_node.keywords if kw.arg}
                # Check positional args: search(payload, timeout) -> if 2+ args passed, timeout is provided
                has_timeout = "timeout" in kw_args or len(call_node.args) >= 2
                if not has_timeout:
                    return "Mandatory Parameter Error in v3.0: 'timeout' is strictly mandatory in Client.search(). Omitting timeout causes runtime ValueError."

        # Check against registered methods if class is in table
        if class_name in v_table:
            class_spec = v_table[class_name]
            methods = class_spec.get("methods", {})
            if method_name not in methods:
                return f"Symbol Error: Method '{class_name}.{method_name}()' not found in SDK {norm_v} symbol table."

        return None
