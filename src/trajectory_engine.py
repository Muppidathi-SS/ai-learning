"""
Trajectory Metrics Engine & Assertion Suite for Week 8 Engineering Challenge.
Provides:
  - Telemetry tracking: Tool-Choice Accuracy (in expected sequences), Argument Validity Rate,
    Step Efficiency (both actual/optimal and optimal/actual), Cost Distribution (p50 & Max).
  - Flexible Path Assertions: Accommodates queries with multiple legitimate tool paths via path sets.
  - Failure Mode Taxonomy Classifier: FM-1 through FM-5.
  - Outcome vs Trajectory Gap Evaluator.
"""

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import statistics
from typing import Any, Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OPENAPI_SPECS_PATH = DATA_DIR / "openapi_specs.json"
DEPRECATIONS_PATH = DATA_DIR / "deprecations.json"


class FailureMode(str, Enum):
    FM1_TOOL_BYPASS = "FM-1: Tool Bypass (Shortcut Memorization)"
    FM2_INVALID_ARGUMENT = "FM-2: Hallucinated / Invalid Tool Argument"
    FM3_REDUNDANT_LOOP = "FM-3: Inefficient Looping / Step Overrun"
    FM4_OUT_OF_ORDER = "FM-4: Out-of-Order Tool Sequencing"
    FM5_PREMATURE_EXIT = "FM-5: Premature Exit / Incomplete Trajectory"
    NONE = "Pass (No Failure Mode)"


@dataclass
class ToolCallObservation:
    iteration: int
    tool: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    valid_tool_choice: bool = True
    valid_sequence_step: bool = True
    valid_arguments: bool = True
    argument_error: Optional[str] = None


@dataclass
class TrajectoryEvaluationResult:
    question_id: str
    question: str
    outcome_passed: bool
    trajectory_passed: bool
    is_false_positive: bool  # outcome_passed is True but trajectory_passed is False
    executed_tools: List[str]
    tool_observations: List[ToolCallObservation]
    matched_path: Optional[List[str]] = None
    failure_modes: List[FailureMode] = field(default_factory=list)
    optimal_steps: int = 3
    actual_steps: int = 0
    step_efficiency: float = 1.0
    cost_usd: float = 0.0
    tokens_used: int = 0
    latency_s: float = 0.0
    detailed_notes: str = ""


# Load schemas for validation
def _get_known_specs() -> Dict[str, Any]:
    if OPENAPI_SPECS_PATH.exists():
        with open(OPENAPI_SPECS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _get_known_deprecations() -> List[Dict[str, Any]]:
    if DEPRECATIONS_PATH.exists():
        with open(DEPRECATIONS_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("deprecations", [])
    return []


KNOWN_SPECS = _get_known_specs()
KNOWN_DEPRECATIONS = _get_known_deprecations()


class FlexibleTrajectoryValidator:
    """
    Validates agent trajectory against flexible path sets.
    Accommodates multiple valid execution paths while enforcing strict semantic validity.
    """

    def __init__(self):
        self.known_specs = KNOWN_SPECS
        self.known_deprecations = KNOWN_DEPRECATIONS

    def validate_argument(self, tool_name: str, args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Checks if tool arguments contain real endpoints, valid versions, and proper parameters."""
        if tool_name == "get_openapi_spec":
            endpoint = args.get("endpoint")
            version = str(args.get("version", ""))
            if not endpoint:
                return False, "Missing 'endpoint' parameter"
            if version not in ["v1", "v2", "v3", "ApiVersion.V1", "ApiVersion.V2", "ApiVersion.V3"]:
                return False, f"Invalid version string '{version}'. Must be v1, v2, or v3."
            clean_ver = "v3" if "v3" in version.lower() else ("v2" if "v2" in version.lower() else "v1")
            endpoints_for_ver = self.known_specs.get(clean_ver, {})
            if endpoint not in endpoints_for_ver:
                return False, f"Hallucinated endpoint '{endpoint}' not found in {clean_ver} OpenAPI specifications."
            return True, None

        elif tool_name == "check_deprecation":
            symbol = args.get("symbol_or_endpoint")
            version = str(args.get("version", ""))
            if not symbol:
                return False, "Missing 'symbol_or_endpoint' parameter"
            if version not in ["v1", "v2", "v3", "ApiVersion.V1", "ApiVersion.V2", "ApiVersion.V3"]:
                return False, f"Invalid version string '{version}'"
            return True, None

        elif tool_name == "search_docs":
            query = args.get("query")
            version = str(args.get("version", ""))
            if not query or not str(query).strip():
                return False, "Empty docs search query"
            if version not in ["v1", "v2", "v3", "ApiVersion.V1", "ApiVersion.V2", "ApiVersion.V3"]:
                return False, f"Invalid version string '{version}'"
            return True, None

        return False, f"Unknown tool '{tool_name}'"

    def evaluate_query_trajectory(
        self,
        q_meta: Dict[str, Any],
        agent_result: Dict[str, Any],
    ) -> TrajectoryEvaluationResult:
        q_id = q_meta["id"]
        q_text = q_meta["question"]
        allowed_paths: List[List[str]] = q_meta.get("allowed_paths", [])
        optimal_steps: int = q_meta.get("optimal_steps", 3)
        mandatory_tools: Set[str] = set(q_meta.get("mandatory_tools", ["get_openapi_spec"]))

        raw_observations = agent_result.get("tool_observations", [])
        executed_tools = [obs["tool"] for obs in raw_observations]
        actual_steps = len(executed_tools)

        # Parse observations & validate arguments and step sequence validity
        parsed_observations: List[ToolCallObservation] = []
        failure_modes: List[FailureMode] = []

        all_args_valid = True
        prefix_tools: List[str] = []

        for obs in raw_observations:
            t_name = obs["tool"]
            t_args = obs["arguments"]
            prefix_tools.append(t_name)

            # Check if this tool call represents a valid sequence step in any allowed path
            is_valid_sequence_step = False
            for path in allowed_paths:
                if len(prefix_tools) <= len(path) and path[:len(prefix_tools)] == prefix_tools:
                    is_valid_sequence_step = True
                    break

            is_valid_arg, err_msg = self.validate_argument(t_name, t_args)
            if not is_valid_arg:
                all_args_valid = False

            parsed_observations.append(
                ToolCallObservation(
                    iteration=obs.get("iteration", len(parsed_observations) + 1),
                    tool=t_name,
                    arguments=t_args,
                    result=obs.get("result", {}),
                    valid_tool_choice=t_name in ["check_deprecation", "get_openapi_spec", "search_docs"],
                    valid_sequence_step=is_valid_sequence_step,
                    valid_arguments=is_valid_arg,
                    argument_error=err_msg,
                )
            )

        # 1. Check FM-1: Tool Bypass (Missing mandatory tools like get_openapi_spec)
        missing_mandatory = mandatory_tools - set(executed_tools)
        if missing_mandatory:
            failure_modes.append(FailureMode.FM1_TOOL_BYPASS)

        # 2. Check FM-2: Invalid / Hallucinated Arguments
        if not all_args_valid:
            failure_modes.append(FailureMode.FM2_INVALID_ARGUMENT)

        # 3. Check FM-3: Redundant Looping (Repeated tool with same intent or > optimal_steps + 1)
        if len(executed_tools) > len(set(executed_tools)) or actual_steps > optimal_steps:
            failure_modes.append(FailureMode.FM3_REDUNDANT_LOOP)

        # 4. Check FM-4: Out of order execution on dynamic branching
        # If question requires dynamic branching on spec, get_openapi_spec MUST precede search_docs
        if q_meta.get("requires_dynamic_branching", False):
            if "search_docs" in executed_tools and "get_openapi_spec" in executed_tools:
                docs_idx = executed_tools.index("search_docs")
                spec_idx = executed_tools.index("get_openapi_spec")
                if docs_idx < spec_idx:
                    failure_modes.append(FailureMode.FM4_OUT_OF_ORDER)

        # 5. Check FM-5: Premature Exit
        if actual_steps < 2 and not missing_mandatory:
            failure_modes.append(FailureMode.FM5_PREMATURE_EXIT)

        # Match path sets
        matched_path = None
        for path in allowed_paths:
            if executed_tools == path:
                matched_path = path
                break

        # Trajectory passes IF:
        # - It matched one of the flexible allowed path sets
        # - All tool arguments are valid (no hallucinated endpoints)
        # - No failure modes detected (FM-1, FM-2, FM-3, FM-4)
        trajectory_passed = (
            matched_path is not None
            and all_args_valid
            and (FailureMode.FM1_TOOL_BYPASS not in failure_modes)
            and (FailureMode.FM2_INVALID_ARGUMENT not in failure_modes)
            and (FailureMode.FM3_REDUNDANT_LOOP not in failure_modes)
            and (FailureMode.FM4_OUT_OF_ORDER not in failure_modes)
        )

        # Outcome check:
        # Did the output contain valid code and target symbol migration?
        v3_code = agent_result.get("v3_code", "")
        outcome_passed = agent_result.get("success", False) and len(v3_code) > 20 and "# Partial code" not in v3_code

        # False positive: Outcome passed, but trajectory failed
        is_false_positive = outcome_passed and (not trajectory_passed)

        # Step efficiency
        step_eff = round(optimal_steps / max(1, actual_steps), 4) if actual_steps > 0 else 0.0

        if not failure_modes:
            failure_modes.append(FailureMode.NONE)

        notes = []
        if is_false_positive:
            notes.append(f"FALSE POSITIVE: Answer succeeded via ungrounded/flawed trajectory ({', '.join(fm.value for fm in failure_modes)}).")
        elif not trajectory_passed:
            notes.append(f"Trajectory failed: {', '.join(fm.value for fm in failure_modes)}.")
        else:
            notes.append(f"Trajectory verified along valid path: {' -> '.join(executed_tools)}.")

        return TrajectoryEvaluationResult(
            question_id=q_id,
            question=q_text,
            outcome_passed=outcome_passed,
            trajectory_passed=trajectory_passed,
            is_false_positive=is_false_positive,
            executed_tools=executed_tools,
            tool_observations=parsed_observations,
            matched_path=matched_path,
            failure_modes=failure_modes,
            optimal_steps=optimal_steps,
            actual_steps=actual_steps,
            step_efficiency=step_eff,
            cost_usd=agent_result.get("cost_usd", 0.0),
            tokens_used=agent_result.get("tokens_used", 0),
            latency_s=agent_result.get("latency_s", 0.0),
            detailed_notes=" ".join(notes),
        )


class TrajectoryTelemetryEngine:
    """
    Aggregates and computes the 4 primary telemetry dimensions across test runs:
      1. Tool-Choice Accuracy (%)
      2. Argument Validity Rate (%)
      3. Step Efficiency (actual relative to optimal)
      4. Cost Distribution (p50 median and Max worst-case loop)
    """

    def __init__(self, results: List[TrajectoryEvaluationResult]):
        self.results = results

    def compute_telemetry(self) -> Dict[str, Any]:
        total_steps = sum(r.actual_steps for r in self.results)
        if total_steps == 0:
            return {
                "tool_choice_accuracy_pct": 0.0,
                "argument_validity_pct": 0.0,
                "step_efficiency_ratio": 0.0,
                "cost_p50_usd": 0.0,
                "cost_max_usd": 0.0,
                "cost_variance_ratio_pct": 0.0,
                "outcome_pass_rate_pct": 0.0,
                "trajectory_pass_rate_pct": 0.0,
                "outcome_vs_trajectory_gap_pct": 0.0,
            }

        # 1. Tool-Choice Accuracy: % of steps selecting valid tools in expected sequences
        valid_sequence_steps = sum(
            sum(1 for obs in r.tool_observations if obs.valid_sequence_step)
            for r in self.results
        )
        tool_choice_accuracy = (valid_sequence_steps / total_steps) * 100.0

        # 2. Argument Validity Rate: % of tool calls passing valid parameters
        valid_arguments = sum(
            sum(1 for obs in r.tool_observations if obs.valid_arguments)
            for r in self.results
        )
        argument_validity_rate = (valid_arguments / total_steps) * 100.0

        # 3. Step Efficiency: Ratio of actual steps taken relative to optimal steps needed
        total_optimal = sum(r.optimal_steps for r in self.results)
        step_efficiency_actual_over_optimal = (total_steps / total_optimal) if total_optimal > 0 else 1.0
        step_efficiency_optimal_over_actual = (total_optimal / total_steps) if total_steps > 0 else 1.0

        # 4. Cost Distribution: p50 and Max (worst-case loop)
        costs = [r.cost_usd for r in self.results]
        cost_p50 = statistics.median(costs) if costs else 0.0
        cost_max = max(costs) if costs else 0.0
        cost_variance_ratio = ((cost_max - cost_p50) / cost_p50 * 100.0) if cost_p50 > 0 else 0.0

        # Pass rates & Gap
        n = len(self.results)
        outcome_pass_rate = (sum(1 for r in self.results if r.outcome_passed) / n) * 100.0
        trajectory_pass_rate = (sum(1 for r in self.results if r.trajectory_passed) / n) * 100.0
        gap = outcome_pass_rate - trajectory_pass_rate

        return {
            "total_queries": n,
            "total_steps": total_steps,
            "total_optimal_steps": total_optimal,
            "tool_choice_accuracy_pct": round(tool_choice_accuracy, 2),
            "argument_validity_pct": round(argument_validity_rate, 2),
            "step_efficiency_actual_over_optimal": round(step_efficiency_actual_over_optimal, 4),
            "step_efficiency_optimal_over_actual": round(step_efficiency_optimal_over_actual, 4),
            "cost_p50_usd": round(cost_p50, 6),
            "cost_max_usd": round(cost_max, 6),
            "cost_variance_ratio_pct": round(cost_variance_ratio, 2),
            "outcome_pass_rate_pct": round(outcome_pass_rate, 2),
            "trajectory_pass_rate_pct": round(trajectory_pass_rate, 2),
            "outcome_vs_trajectory_gap_pct": round(gap, 2),
            "false_positive_count": sum(1 for r in self.results if r.is_false_positive),
        }

    def count_failure_modes(self) -> Dict[str, int]:
        counts = {
            FailureMode.FM1_TOOL_BYPASS.value: 0,
            FailureMode.FM2_INVALID_ARGUMENT.value: 0,
            FailureMode.FM3_REDUNDANT_LOOP.value: 0,
            FailureMode.FM4_OUT_OF_ORDER.value: 0,
            FailureMode.FM5_PREMATURE_EXIT.value: 0,
        }
        for r in self.results:
            for fm in r.failure_modes:
                if fm.value in counts:
                    counts[fm.value] += 1
        return counts
