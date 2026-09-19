"""
Tests for Week 7 Bonus Challenge:
Demonstrates that a user's preferred SDK version mentioned in turn 2 survives
into turn 28 despite multiple sliding window evictions.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.memory import SlidingWindowSummaryMemory


def test_sliding_window_survives_evictions():
    mem = SlidingWindowSummaryMemory(window_size=6)

    # Turn 1
    mem.add_turn("user", "Hello assistant, we are starting our migration plan.")
    mem.add_turn("assistant", "Hello! I am here to help you migrate your SDK calls.")

    # Turn 2: User states critical pinned version constraint
    mem.add_turn("user", "IMPORTANT: Our team has pinned our target SDK version strictly to v3. Never generate v1 or v2 code.")
    mem.add_turn("assistant", "Acknowledged. I will strictly target SDK version v3 for all code generation.")

    # Turns 3 - 27: Intervening questions and conversation that overflow the sliding window
    for turn in range(5, 28):
        if turn % 2 == 1:
            mem.add_turn("user", f"Can you explain endpoint behavior for module #{turn}?")
        else:
            mem.add_turn("assistant", f"Module #{turn-1} provides standard data streaming and configuration utilities.")

    # Verify that by Turn 27, multiple evictions occurred
    assert mem.eviction_count >= 2, f"Expected at least 2 evictions, got {mem.eviction_count}"

    # Turn 28: Ask about the pinned version
    query_turn = mem.add_turn("user", "Quick check before release: Which SDK version is my project pinned to?")
    response = mem.answer_query("Which SDK version is my project pinned to?")

    print(f"\n[Turn 28 Query Response]: {response}")
    print(f"[Total Evictions Recorded]: {mem.eviction_count}")
    for log in mem.eviction_logs:
        print(f"  -> {log}")

    assert "v3" in response, f"Expected 'v3' in response, got: {response}"
    assert mem.eviction_count >= 2


if __name__ == "__main__":
    test_sliding_window_survives_evictions()
    print("\n[PASS] Week 7 Bonus Challenge Passed: Turn 2 preference survived into Turn 28 across evictions!")
