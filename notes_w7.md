# Week 7 Practical — Notes & Implementation Summary

## 1. Tool Registration & Design
Added `check_deprecation` with zero description overlap with `search_docs` and `get_openapi_spec`:
- **`search_docs`**: Searches prose documentation and markdown examples.
- **`get_openapi_spec`**: Retrieves OpenAPI schema specs, parameters, and responses.
- **`check_deprecation`**: Queries changelog/deprecation registry to discover deprecated symbols and their replacements.
- **`ApiVersion`**: Strongly-typed `Enum` (`v1`, `v2`, `v3`).

Git Diff (3-line tool registration):
```diff
 AVAILABLE_TOOLS = {
     "search_docs": search_docs,
     "get_openapi_spec": get_openapi_spec,
+    "check_deprecation": check_deprecation,
 }
```

## 2. Race Results (Across 10 Migration Questions)
Reported in `race.csv`:

| System | Pass Rate (%) | p50 Latency (s) | Total Tokens | Cost Per Question ($) |
| :--- | :--- | :--- | :--- | :--- |
| **Fixed Workflow** | 100.0% | 0.0011 | 3,700 | $0.000740 |
| **Autonomous Agent** | 100.0% | 0.0013 | 10,612 | $0.001747 |

## 3. Four Budget Enforcements (`budget_termination.log`)
The agent loop strictly enforces all 4 budgets:
1. `max_iterations`: Exits cleanly when iteration limit is reached.
2. `max_tokens`: Exits cleanly when cumulative tokens across all laps exceed limit.
3. `max_cost`: Exits cleanly when accumulated dollar cost exceeds limit.
4. `wall_clock_seconds`: Exits cleanly when elapsed wall clock time exceeds limit.

All 4 terminations logged in `budget_termination.log`.

## 4. Bonus Challenge: Sliding Window Memory with Summarization
- Thread length: 30 turns.
- In Turn 2, the user pinned the target SDK version strictly to `v3`.
- Active window size: 6 turns.
- Over 30 turns, 4 window evictions occurred.
- At Turn 28, query verified that the pinned SDK version `v3` survived into active context from summarized memory.
- Tested and verified in `tests/test_bonus_memory.py`.
