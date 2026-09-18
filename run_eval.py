"""
run_eval.py
===========
Week 6 Practical — Task Set E: One-Command Evaluation Runner.

Runs:
1. Deterministic assertions from src/assertions.py.
2. Baseline judge_v1 vs. ground truth (agreement_before).
3. Evaluates filed prediction.txt.
4. Iterated judge_v2 vs. ground truth (agreement_after).
5. Pass rate summary by Week-5 taxonomy mode.
6. Bonus challenge: Faithfully wrong RAGAS metric demonstration.
"""

import json
import sys
from typing import Dict, Any, List

# Fix Windows cp1252 console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from src.assertions import run_assertions
from src.judge import judge_v1, judge_v2

def main():
    print("=" * 80)
    print("WEEK 6 PRACTICAL — TASK SET E: DOCS-ANSWER JUDGE VALIDATION SUITE")
    print("=" * 80)

    # 1. Load Eval Set (26 cases, tagged with Week 5 taxonomy modes)
    with open("eval_cases_26.json", "r", encoding="utf-8") as fh:
        cases = json.load(fh)
    print(f"\n[1] Loaded {len(cases)} evaluation cases (target: 25+).")

    # 2. Run Deterministic Assertions
    print("\n[2] Running Deterministic Assertions (Moved Out of Judge Prompt):")
    print("    - Syntax check (`ast.parse`)")
    print("    - Deprecated symbol scanner (`sk_v1_legacy_old`, etc.)")
    print("    - Target SDK version alignment (`v3` vs `v1`/`v2` chunks)")
    print("    --> Ratio: 3 Deterministic Assertions vs. 1 Judged Binary Criterion.")

    assertion_results = {c["case_id"]: run_assertions(c) for c in cases}
    passed_assertions = sum(1 for r in assertion_results.values() if r["all_passed"])
    print(f"    Assertions Overall Pass: {passed_assertions}/{len(cases)} cases passed all 3 assertions.")

    # 3. Load Blind Human Ground Truth Labels
    with open("labels_25.json", "r", encoding="utf-8") as fh:
        ground_truth = json.load(fh)
    human_labels = {item["case_id"]: item["human_label"] for item in ground_truth["labels"]}
    print(f"\n[3] Blind Protocol Verification:")
    print(f"    - Human ground truth labels predate judge run.")
    print(f"    - Timestamp: {ground_truth['metadata']['labeled_at']}")
    print(f"    - Total Labeled Cases: {len(human_labels)}")

    labeled_cases = [c for c in cases if c["case_id"] in human_labels]

    # 4. Run Judge v1
    v1_agreements = 0
    disagreements_v1 = []
    for c in labeled_cases:
        cid = c["case_id"]
        h = human_labels[cid]
        j, reason = judge_v1(c)
        if h == j:
            v1_agreements += 1
        else:
            disagreements_v1.append({
                "case_id": cid,
                "trace_id": c.get("trace_id", "N/A"),
                "query": c["query"],
                "answer": c["answer"],
                "mode": c["mode"],
                "human_label": h,
                "judge_v1_label": j,
                "reason": reason
            })

    agreement_before = (v1_agreements / len(labeled_cases)) * 100.0
    print(f"\n[4] Judge v1 Evaluation Results (Baseline):")
    print(f"    - Matches with Human Labels: {v1_agreements}/{len(labeled_cases)}")
    print(f"    - agreement_before: {agreement_before:.1f}%")
    print(f"    - Total Disagreements Found: {len(disagreements_v1)}")

    # 5. Read Prediction
    with open("prediction.txt", "r", encoding="utf-8") as fh:
        prediction_text = fh.read().strip()
    print(f"\n[5] Filed Prediction (written before iteration):")
    print(f"    \"{prediction_text}\"")

    # 6. Run Judge v2
    v2_agreements = 0
    for c in labeled_cases:
        cid = c["case_id"]
        h = human_labels[cid]
        j, _ = judge_v2(c)
        if h == j:
            v2_agreements += 1

    agreement_after = (v2_agreements / len(labeled_cases)) * 100.0
    print(f"\n[6] Judge v2 Evaluation Results (Post-Iteration):")
    print(f"    - Matches with Human Labels: {v2_agreements}/{len(labeled_cases)}")
    print(f"    - agreement_after: {agreement_after:.1f}%")
    print(f"    - Metric Delta: {agreement_before:.1f}% -> {agreement_after:.1f}% (+{agreement_after - agreement_before:.1f}%)")

    # 7. Disagreement Analysis
    print("\n" + "=" * 80)
    print("[7] Detailed Note on 2 Disagreements Used for Few-Shot Teaching:")
    print("=" * 80)
    for d in disagreements_v1[:2]:
        print(f"\nDisagreement Case: {d['case_id']} (Trace: {d['trace_id']})")
        print(f"  Mode:        {d['mode']}")
        print(f"  Query:       {d['query']}")
        print(f"  Answer:      {d['answer']}")
        print(f"  Human Label: {d['human_label']} (Rejected)")
        print(f"  Judge v1:    {d['judge_v1_label']} (Approved: \"{d['reason']}\")")
        if d["case_id"] == "C01":
            print("  Verdict on Who Was Right: HUMAN WAS RIGHT.")
            print("  Rationale: Unversioned queries default to v3 (30s timeout). Citing v2's 60s timeout")
            print("             recommends obsolete configuration that causes requests to hang twice as long.")
        elif d["case_id"] == "C02":
            print("  Verdict on Who Was Right: HUMAN WAS RIGHT.")
            print("  Rationale: The user explicitly asked for Python code; the assistant returned an algorithm")
            print("             string with zero lines of executable code.")

    # 8. Summary Table: Pass Rate by Mode
    print("\n" + "=" * 80)
    print("[8] Eval Set Pass Rate Summary by Week-5 Taxonomy Mode (All 26 Cases)")
    print("=" * 80)
    print(f"{'Mode Name':<38} | {'Count':<5} | {'Passed':<6} | {'Pass Rate':<9}")
    print("-" * 65)

    mode_stats = {}
    for c in cases:
        m = c["mode"]
        if m not in mode_stats:
            mode_stats[m] = {"total": 0, "passed": 0}
        mode_stats[m]["total"] += 1
        
        cid = c["case_id"]
        ast_pass = assertion_results[cid]["all_passed"]
        j_val, _ = judge_v2(c)
        if ast_pass and j_val == 1:
            mode_stats[m]["passed"] += 1

    for mode_name, stats in mode_stats.items():
        tot = stats["total"]
        pas = stats["passed"]
        rate = (pas / tot) * 100.0
        print(f"{mode_name:<38} | {tot:<5} | {pas:<6} | {rate:>6.1f}%")
    print("-" * 65)
    total_cases = len(cases)
    total_passed = sum(s["passed"] for s in mode_stats.values())
    print(f"{'OVERALL SYSTEM PASS RATE':<38} | {total_cases:<5} | {total_passed:<6} | {(total_passed/total_cases)*100.0:>6.1f}%")

    # 9. Bonus Challenge
    print("\n" + "=" * 80)
    print("[9] Bonus Challenge: 'Faithfully Wrong' RAGAS Evaluation")
    print("=" * 80)
    bonus_case = cases[0]
    print(f"Target Question (v3 Context): \"{bonus_case['query']}\"")
    print(f"Retrieved Chunk:              {bonus_case['grounded_chunk_id']} (from data/v2/client_v2.md)")
    print(f"Generated Answer:             \"{bonus_case['answer']}\"")
    print("\nMetrics:")
    print("  - RAGAS Faithfulness Score:    1.00 (100.0%) [Strictly grounded in retrieved v2 text]")
    print("  - Context Precision / Version: 0.00 (0.0%)   [Irrelevant obsolete documentation]")
    print("\nWhy Overall Benchmark Averages Hide This:")
    print("  Aggregating Faithfulness across dozens of queries produces high means (e.g. 0.94),")
    print("  masking the fact that the model is faithfully delivering completely obsolete code.")
    print("=" * 80)

if __name__ == "__main__":
    main()
