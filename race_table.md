# Week 10 Race Table: Single Agent vs. Orchestrator Squad

## 1. Executive Summary Table (4 Telemetry Dimensions)

| Metric | Single Agent (Arm A) | Orchestrator Squad (Arm B) | Performance Delta / Penalty |
| :--- | :---: | :---: | :---: |
| **Pass Rate (%)** | **100.0%** | **100.0%** | **0.0%** (Identical functional accuracy) |
| **p50 Latency (s)** | **0.0011s** | **0.0018s** | **1.6x slower** (+63.6%) |
| **p99 Latency (s)** | **0.0017s** | **0.0020s** | **1.2x slower** |
| **Total Tokens** | **11194** | **17412** | **1.6x Context Re-Send Multiplier** |
| **Cost Per Question ($)** | **$0.001769** | **$0.002772** | **+56.7% cost explosion** |

---

## 2. Multiplier Calculation & Bottleneck Attribution

- **Context Re-Send Multiplier Formula:**
  $$\text{Context Re-Send Multiplier} = \frac{\text{Multi-Agent Total Tokens}}{\text{Single Agent Total Tokens}} = \frac{17412}{11194} = \mathbf{1.6\times}$$

- **Largest Token Bottleneck:**
  - **Dominant Handoff Step:** **`orchestrator -> code-sample worker resend`** accounting for **53.5%** of all multi-agent tokens (9323/17412 tokens).
  - **Root Cause:** Because the code-sample specialist operates in an isolated stateless context, the Orchestrator must re-serialize the entire upstream conversation, user query, and Worker 1's full JSON output into Worker 2's prompt.

---

## 3. Per-Case Comparison Breakdown (10 Evaluation Cases)

| Case ID | Primary Symbol | Single Agent Tokens | Squad Total Tokens | Single Latency (s) | Squad Latency (s) | Single Cost ($) | Squad Cost ($) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `q1` | `Client.send` | 1343 | 2256 | 0.0017s | 0.0019s | $0.002100 | $0.003568 |
| `q2` | `Auth.login` | 884 | 1572 | 0.0012s | 0.0018s | $0.001416 | $0.002508 |
| `q3` | `Stream.feed` | 939 | 1748 | 0.0011s | 0.0019s | $0.001502 | $0.002787 |
| `q4` | `Batch.dispatch` | 1749 | 1787 | 0.0012s | 0.0018s | $0.002715 | $0.002841 |
| `q5` | `Config.get_config` | 910 | 1684 | 0.0012s | 0.0020s | $0.001453 | $0.002677 |
| `q6` | `Webhook.subscribe` | 917 | 1697 | 0.0011s | 0.0019s | $0.001465 | $0.002711 |
| `q7` | `Client.send` | 898 | 1636 | 0.0011s | 0.0018s | $0.001435 | $0.002605 |
| `q8` | `Stream.feed` | 932 | 1721 | 0.0011s | 0.0018s | $0.001491 | $0.002746 |
| `q9` | `Batch.dispatch` | 1728 | 1699 | 0.0011s | 0.0018s | $0.002684 | $0.002709 |
| `q10` | `Auth.login` | 894 | 1612 | 0.0011s | 0.0018s | $0.001431 | $0.002568 |
