# Decision Rule Verdict: Agent vs. Fixed Workflow

Use the fixed workflow for routine, predictable migrations: across 10 questions both achieved 100.0% pass rate, but the workflow required only 3,700 total tokens and $0.000740/question at 0.0011s latency, whereas the agent consumed 10,612 tokens and $0.001747/question (2.36x cost) at 0.0013s latency.

However, this team must deploy the autonomous agent whenever execution paths vary by input — specifically when tool findings in step 2 (e.g., conditional WebSocket 101 upgrades or dynamic OpenAPI parameters like `auto_retry_failed`) dictate non-linear downstream steps that cannot be pre-wired into a rigid 3-step pipeline without exponential combinatorial branching.
