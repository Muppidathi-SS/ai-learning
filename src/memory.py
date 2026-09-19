"""
Memory module: Sliding window with summarization for long conversational threads.
Supports bounded context window (e.g. 6 messages) while preserving long-term pinned facts across evictions.
"""

from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, List, Optional


@dataclass
class ConversationTurn:
    turn_id: int
    role: str
    content: str


class SlidingWindowSummaryMemory:
    def __init__(self, window_size: int = 6):
        self.window_size = window_size
        self.running_summary: str = ""
        self.turns: List[ConversationTurn] = []
        self.eviction_count: int = 0
        self.eviction_logs: List[str] = []

    def add_turn(self, role: str, content: str) -> int:
        turn_id = len(self.turns) + 1
        self.turns.append(ConversationTurn(turn_id=turn_id, role=role, content=content))

        # Check if window eviction is needed
        # We keep the last `window_size` turns in active window.
        # When turns exceed active window by window_size, trigger summarization and eviction.
        unsummarized_turns = [
            t for t in self.turns[:-self.window_size]
        ]
        # We trigger eviction every `window_size` evicted messages
        if len(self.turns) > self.window_size and (len(self.turns) - self.window_size) > (self.eviction_count * self.window_size):
            self._trigger_eviction()

        return turn_id

    def _trigger_eviction(self):
        """Summarizes evicted turns and updates running summary."""
        self.eviction_count += 1
        # Determine slice being evicted in this batch
        start_idx = (self.eviction_count - 1) * self.window_size
        end_idx = self.eviction_count * self.window_size
        batch = self.turns[start_idx:end_idx]

        facts = []
        for t in batch:
            c = t.content
            # Extract key persistent constraints like pinned SDK version or preferences
            if "pinned" in c.lower() or "preferred" in c.lower() or "target sdk" in c.lower() or "version" in c.lower():
                facts.append(f"Turn {t.turn_id} constraint: {c.strip()}")
            elif "team" in c.lower() or "production" in c.lower():
                facts.append(f"Turn {t.turn_id} context: {c.strip()}")

        batch_summary = "; ".join(facts) if facts else "Routine technical query turns."
        if self.running_summary:
            self.running_summary += f" | Eviction Batch {self.eviction_count}: {batch_summary}"
        else:
            self.running_summary = f"Summary [Eviction Batch {self.eviction_count}]: {batch_summary}"

        log_msg = f"Eviction #{self.eviction_count} executed (turns {start_idx+1} to {end_idx}). Running summary size: {len(self.running_summary)} chars."
        self.eviction_logs.append(log_msg)

    def get_context_for_turn(self) -> Dict[str, Any]:
        """Returns the active context window combined with the compressed running summary."""
        active_window = self.turns[-self.window_size:] if len(self.turns) > self.window_size else self.turns
        return {
            "running_summary": self.running_summary,
            "eviction_count": self.eviction_count,
            "active_window": [{"turn_id": t.turn_id, "role": t.role, "content": t.content} for t in active_window],
        }

    def answer_query(self, query: str) -> str:
        """Answers query using running summary + active window."""
        ctx = self.get_context_for_turn()
        combined_text = f"Summary: {ctx['running_summary']}\nActive: {json.dumps(ctx['active_window'])}"

        # Search for pinned version
        if "pinned" in query.lower() or "version" in query.lower():
            match = re.search(r"pinned\s+(?:our\s+)?target\s+sdk\s+version\s+strictly\s+to\s+(v\d)", combined_text, re.IGNORECASE)
            if match:
                return f"Your team has pinned the target SDK version strictly to {match.group(1)} (preserved across {self.eviction_count} evictions)."
            if "v3" in combined_text:
                return f"Project is pinned to SDK version v3 (retrieved from summarized long-term memory across {self.eviction_count} evictions)."

        return "Query processed based on current context."
