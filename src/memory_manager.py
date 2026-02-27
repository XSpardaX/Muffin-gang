"""Loads/saves character memory summaries and builds memory context per turn."""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .types import CHARACTER_IDS, CharacterId, MemorySummary, TranscriptTurn


def _empty_summary(character_id: CharacterId) -> MemorySummary:
    return MemorySummary(
        character_id=character_id,
        core_alibi="",
        timeline_summary="",
        relationships_and_attitude="",
        key_claims=[],
        known_self_contradictions=[],
        known_inter_contradictions=[],
        lie_patterns="",
        last_updated_turn_id=0,
    )


class MemoryManager:
    """Manages per-character memory summaries and memory context for prompts."""

    def __init__(self, base_session_data_dir: str) -> None:
        self._base = Path(base_session_data_dir)

    def _session_dir(self, session_id: str) -> Path:
        return self._base / f"session_{session_id}"

    def _summary_path(self, session_id: str, character_id: CharacterId) -> Path:
        return self._session_dir(session_id) / f"{character_id}_memory_summary.json"

    def initialize_session(self, session_id: str, character_ids: Optional[List[CharacterId]] = None) -> None:
        ids = character_ids or CHARACTER_IDS
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        for cid in ids:
            path = self._summary_path(session_id, cid)
            if not path.exists():
                self.save_memory_summary(session_id, _empty_summary(cid))

    def load_memory_summary(self, session_id: str, character_id: CharacterId) -> MemorySummary:
        path = self._summary_path(session_id, character_id)
        if not path.exists():
            return _empty_summary(character_id)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return MemorySummary.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return _empty_summary(character_id)

    def save_memory_summary(self, session_id: str, summary: MemorySummary) -> None:
        path = self._summary_path(session_id, summary.character_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

    def get_memory_context_for_turn(
        self,
        session_id: str,
        character_id: CharacterId,
        recent_turns: List[TranscriptTurn],
        contradiction_notes: List[str],
        max_recent_turns: int = 5,
    ) -> Dict[str, Any]:
        summary = self.load_memory_summary(session_id, character_id)
        recent = recent_turns[-max_recent_turns:] if len(recent_turns) > max_recent_turns else recent_turns
        return {
            "summary": summary,
            "recent_turns": recent,
            "contradiction_notes": contradiction_notes,
        }

    def maybe_summarize_character(
        self,
        session_id: str,
        character_id: CharacterId,
        all_turns: List[TranscriptTurn],
    ) -> MemorySummary:
        summary = self.load_memory_summary(session_id, character_id)
        if len(all_turns) <= 3:
            return summary
        last_turn_id = max((t.turn_id for t in all_turns), default=0)
        if last_turn_id <= summary.last_updated_turn_id:
            return summary
        key_claims: List[str] = []
        for t in all_turns:
            for c in t.structured_claims:
                subj = c.get("subject", character_id)
                action = c.get("action", "")
                time_val = c.get("time", "")
                loc = c.get("location", "")
                key_claims.append(f"{subj}: {action}" + (f" at {time_val}" if time_val else "") + (f" in {loc}" if loc else ""))
        summary = MemorySummary(
            character_id=character_id,
            core_alibi=summary.core_alibi or "Not yet stated.",
            timeline_summary=summary.timeline_summary or "Timeline not yet established.",
            relationships_and_attitude=summary.relationships_and_attitude,
            key_claims=key_claims[-20:],
            known_self_contradictions=summary.known_self_contradictions,
            known_inter_contradictions=summary.known_inter_contradictions,
            lie_patterns=summary.lie_patterns,
            last_updated_turn_id=last_turn_id,
        )
        self.save_memory_summary(session_id, summary)
        return summary

    def recover_from_crash(self, session_id: str, character_ids: Optional[List[CharacterId]] = None) -> None:
        ids = character_ids or CHARACTER_IDS
        session_dir = self._session_dir(session_id)
        if not session_dir.exists():
            return
        for f in session_dir.glob("*.tmp"):
            try:
                f.unlink()
            except OSError:
                pass
