"""
Race Runner for Week 7 Practical Task Set E.
Races the autonomous docs agent against the fixed 3-step workflow across 10 migration questions.
Computes and outputs:
  - Pass rate (%)
  - p50 latency (s)
  - Total tokens (summed over all laps)
  - Cost per question ($)
Outputs race.csv and budget_termination.log.
"""

import csv
import json
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools import ApiVersion
from src.agent import MigrationAgent, AgentBudgets, BUDGET_LOG_PATH
from src.workflow import run_workflow

QUESTIONS_PATH = PROJECT_ROOT / "questions_10.json"
RACE_CSV_PATH = PROJECT_ROOT / "race.csv"


def load_questions() -> List[Dict[str, Any]]:
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_race():
    print("================================================================")
    print("WEEK 7 PRACTICAL — TASK SET E: AGENT VS FIXED WORKFLOW RACE")
    print("================================================================")

    questions = load_questions()
    print(f"Loaded {len(questions)} migration questions (at least 3 dynamic branching cases).\n")

    # Clear previous budget termination log cleanly without unlink collision
    if BUDGET_LOG_PATH.exists():
        with open(BUDGET_LOG_PATH, "w", encoding="utf-8") as f:
            pass

    # 1. Run Fixed Workflow
    print("Running Fixed 3-Step Workflow...")
    workflow_results = []
    for q in questions:
        q_text = q["question"]
        cur_v = ApiVersion.from_str(q.get("current_version", "v2"))
        tgt_v = ApiVersion.from_str(q.get("target_version", "v3"))
        res = run_workflow(q_text, cur_v, tgt_v)
        workflow_results.append(res)

    # 2. Run Autonomous Agent
    print("Running Autonomous Migration Agent...")
    agent = MigrationAgent()
    agent_results = []
    for q in questions:
        q_text = q["question"]
        cur_v = ApiVersion.from_str(q.get("current_version", "v2"))
        tgt_v = ApiVersion.from_str(q.get("target_version", "v3"))
        res = agent.run(q_text, cur_v, tgt_v)
        agent_results.append(res)

    # 3. Calculate 4 Numbers for both systems
    # Pass rate (%)
    wf_pass_rate = (sum(1 for r in workflow_results if r["success"]) / len(workflow_results)) * 100.0
    ag_pass_rate = (sum(1 for r in agent_results if r["success"]) / len(agent_results)) * 100.0

    # p50 latency (s)
    wf_p50_latency = statistics.median([r["latency_s"] for r in workflow_results])
    ag_p50_latency = statistics.median([r["latency_s"] for r in agent_results])

    # Total tokens (summed over all laps)
    wf_total_tokens = sum(r["tokens_used"] for r in workflow_results)
    ag_total_tokens = sum(r["tokens_used"] for r in agent_results)

    # Cost per question ($)
    wf_cost_per_q = sum(r["cost_usd"] for r in workflow_results) / len(workflow_results)
    ag_cost_per_q = sum(r["cost_usd"] for r in agent_results) / len(agent_results)

    # Output race.csv
    headers = ["System", "Pass Rate (%)", "p50 Latency (s)", "Total Tokens", "Cost Per Question ($)"]
    rows = [
        ["Fixed Workflow", f"{wf_pass_rate:.1f}%", f"{wf_p50_latency:.4f}", wf_total_tokens, f"${wf_cost_per_q:.6f}"],
        ["Autonomous Agent", f"{ag_pass_rate:.1f}%", f"{ag_p50_latency:.4f}", ag_total_tokens, f"${ag_cost_per_q:.6f}"],
    ]

    with open(RACE_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print("\n----------------------------------------------------------------")
    print("RACE RESULTS (race.csv)")
    print("----------------------------------------------------------------")
    print(f"{'System':<20} | {'Pass Rate (%)':<14} | {'p50 Latency':<14} | {'Total Tokens':<14} | {'Cost / Q ($)':<14}")
    print("-" * 84)
    for r in rows:
        print(f"{r[0]:<20} | {r[1]:<14} | {r[2]:<14} | {r[3]:<14} | {r[4]:<14}")
    print("----------------------------------------------------------------\n")

    # 4. Stress Test and Enforce All Four Budgets
    print("Enforcing All Four Budgets on Agent Loop...")
    budget_tests = [
        {"name": "max_iterations", "budgets": AgentBudgets(max_iterations=2), "stress": None},
        {"name": "max_tokens", "budgets": AgentBudgets(max_tokens=300), "stress": "max_tokens"},
        {"name": "max_cost", "budgets": AgentBudgets(max_cost=0.0001), "stress": "max_cost"},
        {"name": "wall_clock_seconds", "budgets": AgentBudgets(wall_clock_seconds=0.10), "stress": "wall_clock_seconds"},
    ]

    for bt in budget_tests:
        test_agent = MigrationAgent(budgets=bt["budgets"])
        test_res = test_agent.run(
            "How do I migrate Client.send to v3?",
            current_version=ApiVersion.V2,
            target_version=ApiVersion.V3,
            force_budget_stress=bt["stress"],
        )
        print(f"  [BUDGET TEST] {bt['name']:<20} -> Fired: {test_res['exit_reason']} | Clean Exit: {test_res['exited_cleanly']}")

    print("\nBudget termination logged to budget_termination.log:")
    if BUDGET_LOG_PATH.exists():
        with open(BUDGET_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                print(f"  {line.strip()}")

    print("\nRace complete successfully!")


if __name__ == "__main__":
    run_race()
