"""Manages on-disk transcripts with circular buffer and crash-safe writes."""
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from .types import CHARACTER_IDS, CharacterId, TranscriptTurn


class TranscriptManager:
    """Circular buffer of max N transcript files per character; crash-safe writes."""

    def __init__(
        self,
        base_transcripts_dir: str,
        max_transcripts_per_character: int = 100,
    ) -> None:
        self._base = Path(base_transcripts_dir)
        self._max = max_transcripts_per_character
        self._index_cache: Dict[str, Dict[CharacterId, Dict[str, int]]] = {}

    def _session_dir(self, session_id: str) -> Path:
        return self._base / f"session_{session_id}"

    def _char_dir(self, session_id: str, character_id: CharacterId) -> Path:
        return self._session_dir(session_id) / character_id

    def _index_path(self, session_id: str, character_id: CharacterId) -> Path:
        return self._char_dir(session_id, character_id) / "index.json"

    def _turn_path(self, session_id: str, character_id: CharacterId, slot: int) -> Path:
        return self._char_dir(session_id, character_id) / f"turn_{slot:03d}.txt"

    def initialize_session(self, session_id: str, character_ids: Optional[List[CharacterId]] = None) -> None:
        ids = character_ids or CHARACTER_IDS
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        for cid in ids:
            char_dir = self._char_dir(session_id, cid)
            char_dir.mkdir(parents=True, exist_ok=True)
            idx_path = self._index_path(session_id, cid)
            if not idx_path.exists():
                self._write_index(session_id, cid, current_index=-1, total_written=0)

    def _read_index(self, session_id: str, character_id: CharacterId) -> Dict[str, int]:
        path = self._index_path(session_id, character_id)
        if not path.exists():
            return {"current_index": -1, "total_written": 0}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "current_index": data.get("current_index", -1),
                "total_written": data.get("total_written", 0),
            }
        except (json.JSONDecodeError, OSError):
            return {"current_index": -1, "total_written": 0}

    def _write_index(self, session_id: str, character_id: CharacterId, current_index: int, total_written: int) -> None:
        path = self._index_path(session_id, character_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "current_index": current_index,
            "total_written": total_written,
            "max_transcripts": self._max,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

    def log_turn(self, session_id: str, character_id: CharacterId, turn: TranscriptTurn) -> None:
        idx = self._read_index(session_id, character_id)
        current = idx["current_index"]
        total = idx["total_written"]
        next_slot = (current + 1) % self._max
        total_new = total + 1

        path = self._turn_path(session_id, character_id, next_slot)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(turn.to_dict(), indent=2, ensure_ascii=False)
        tmp = path.with_suffix(".txt.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

        self._write_index(session_id, character_id, next_slot, total_new)

    def get_character_turns(self, session_id: str, character_id: CharacterId) -> List[TranscriptTurn]:
        idx = self._read_index(session_id, character_id)
        current = idx["current_index"]
        total = idx["total_written"]
        if total == 0:
            return []
        turns: List[TranscriptTurn] = []
        n = min(total, self._max)
        for i in range(n):
            slot = (current - i + self._max) % self._max
            path = self._turn_path(session_id, character_id, slot)
            if not path.exists():
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                turns.append(TranscriptTurn.from_dict(data))
            except (json.JSONDecodeError, OSError):
                continue
        turns.reverse()
        return sorted(turns, key=lambda t: t.turn_id)

    def get_character_last_n_turns(
        self,
        session_id: str,
        character_id: CharacterId,
        n: int,
    ) -> List[TranscriptTurn]:
        all_turns = self.get_character_turns(session_id, character_id)
        return all_turns[-n:] if n > 0 else []

    def get_full_transcript(self, session_id: str) -> List[TranscriptTurn]:
        """Aggregate all character turns into one list sorted by turn_id."""
        seen_turn_ids: set = set()
        out: List[TranscriptTurn] = []
        for cid in CHARACTER_IDS:
            for t in self.get_character_turns(session_id, cid):
                if t.turn_id not in seen_turn_ids:
                    seen_turn_ids.add(t.turn_id)
                    out.append(t)
        out.sort(key=lambda t: (t.turn_id, t.character_id or ""))
        return out

    def get_filtered_transcript_by_character(
        self,
        session_id: str,
        character_id: CharacterId,
    ) -> List[TranscriptTurn]:
        return self.get_character_turns(session_id, character_id)

    def recover_from_crash(self, session_id: str, character_ids: Optional[List[CharacterId]] = None) -> None:
        ids = character_ids or CHARACTER_IDS
        for cid in ids:
            char_dir = self._char_dir(session_id, cid)
            if not char_dir.exists():
                continue
            for f in char_dir.glob("*.tmp"):
                try:
                    f.unlink()
                except OSError:
                    pass
