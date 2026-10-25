"""
Enterprise Conversational Memory Buffer
========================================
Sliding-window multi-turn conversational context manager preserving dialogue state,
tool executions, and context expansion for enterprise AI agents.
Author: Eng. Abdelrahman Rashad (Senior Full-Stack & Solutions Architect).
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

class ConversationalMemory:
    """Manages multi-turn conversation history with a configurable sliding window."""

    def __init__(self, window_size: int = 6):
        self.window_size = window_size
        self.turns: List[Dict[str, Any]] = []

    def add_turn(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Appends a dialogue turn and evicts oldest turns if window capacity is exceeded."""
        turn = {
            "role": role.lower(),
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        self.turns.append(turn)
        if len(self.turns) > self.window_size:
            self.turns = self.turns[-self.window_size:]

    def get_context(self, max_turns: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns the conversation turns up to max_turns."""
        limit = max_turns if max_turns is not None else self.window_size
        return self.turns[-limit:] if limit > 0 else []

    def get_formatted_history(self, max_turns: Optional[int] = None) -> str:
        """Renders turns as a structured text block for prompt expansion."""
        context = self.get_context(max_turns)
        if not context:
            return "No previous conversation history."

        formatted_lines = ["### CONVERSATION HISTORY:"]
        for turn in context:
            role_title = turn["role"].capitalize()
            content = turn["content"].strip()
            formatted_lines.append(f"{role_title}: {content}")

        return "\n".join(formatted_lines)

    def search_history(self, keyword: str) -> List[Dict[str, Any]]:
        """Searches past turns for a specific keyword."""
        kw = keyword.lower()
        return [t for t in self.turns if kw in t["content"].lower()]

    def clear(self):
        """Resets the conversation buffer."""
        self.turns.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes memory state."""
        return {
            "window_size": self.window_size,
            "turn_count": len(self.turns),
            "turns": self.turns
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationalMemory":
        """Hydrates memory state from a dictionary."""
        mem = cls(window_size=data.get("window_size", 6))
        mem.turns = list(data.get("turns", []))
        return mem
