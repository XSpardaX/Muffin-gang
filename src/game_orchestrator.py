"""Game flow: session start, interrogation turns, accusation, reveal."""
import time
from pathlib import Path
from typing import List, Optional, Tuple

from .ai_manager import AIManager
from .analysis_engine import AnalysisEngine
from .memory_manager import MemoryManager
from .state_store import StateStore
from .transcript_manager import TranscriptManager
from .types import CHARACTER_IDS, CharacterId, GameState, TranscriptTurn


def _default_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent


class GameOrchestrator:
    """Coordinates StateStore, AIManager, TranscriptManager, MemoryManager, AnalysisEngine."""

    def __init__(
        self,
        transcripts_dir: Optional[Path] = None,
        session_data_dir: Optional[Path] = None,
        seed: Optional[int] = None,
    ) -> None:
        base = _default_base_dir()
        self.transcripts_dir = transcripts_dir or base / "transcripts"
        self.session_data_dir = session_data_dir or base / "session_data"
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.session_data_dir.mkdir(parents=True, exist_ok=True)

        self.state_store = StateStore(seed=seed)
        self.transcript_manager = TranscriptManager(
            str(self.transcripts_dir),
            max_transcripts_per_character=100,
        )
        self.memory_manager = MemoryManager(str(self.session_data_dir))
        self.ai_manager = AIManager(self.memory_manager, self.transcript_manager)
        self.analysis_engine = AnalysisEngine(self.state_store)

        self._session_id: Optional[str] = None

    def start_game(self, questions_per_character: int = 2) -> Tuple[str, str, GameState]:
        session_id = time.strftime("%Y%m%d-%H%M%S")
        self._session_id = session_id

        self.state_store.initialize_session(session_id, questions_per_character)
        state = self.state_store.state
        assert state is not None

        guilty_id = state.scenario.guilty_character_id
        self.transcript_manager.initialize_session(session_id)
        self.memory_manager.initialize_session(session_id)
        self.ai_manager.initialize_session(session_id, guilty_id)
        self.ai_manager.set_game_state(state)
        self.state_store.set_phase("interrogation")

        intro = (
            "The Grand Muffin has been stolen from the Muffin Gang's vault. "
            "You are interrogating three members: Crumbs, Cherry, and Glaze. "
            f"Each has {questions_per_character} questions. Find the thief.\n"
            "Characters: Crumbs (nervous), Cherry (cocky), Glaze (calm)."
        )
        return session_id, intro, state

    def ask(
        self,
        session_id: str,
        character_id: CharacterId,
        player_question: str,
    ) -> Optional[TranscriptTurn]:
        if self._session_id != session_id or not self.state_store.state:
            return None
        state = self.state_store.state
        if state.phase != "interrogation":
            return None
        cs = self.state_store.get_character_state(character_id)
        if not cs or cs.questions_remaining <= 0:
            return None
        if not self.state_store.use_question(character_id):
            return None

        turn_id = self.state_store.increment_turn()
        suspicion = self.state_store.get_suspicion_snapshot()
        contradiction_notes = self.state_store.get_contradiction_notes_for_character(character_id)

        turn = self.ai_manager.ask_character(
            session_id=session_id,
            character_id=character_id,
            turn_id=turn_id,
            player_question=player_question,
            suspicion_snapshot=suspicion,
            contradictions_for_character=contradiction_notes,
        )
        turn.metadata["suspicion_snapshot"] = suspicion
        self.analysis_engine.process_turn(turn)
        return turn

    def can_ask(self, character_id: CharacterId) -> bool:
        cs = self.state_store.get_character_state(character_id)
        return cs is not None and cs.questions_remaining > 0

    def accuse(self, session_id: str, accused_character_id: CharacterId) -> Tuple[bool, str]:
        if not self.state_store.state or self._session_id != session_id:
            return False, "Invalid session."
        self.state_store.set_phase("accusation")
        guilty_id = self.state_store.get_guilty_character_id()
        correct = guilty_id == accused_character_id
        self.state_store.set_phase("ended")
        self.ai_manager.shutdown_session(session_id)

        if correct:
            reveal = f"You were right. {accused_character_id} stole the Grand Muffin."
        else:
            reveal = f"Wrong. The thief was {guilty_id}, not {accused_character_id}."
        return correct, reveal

    def get_full_transcript(self, session_id: str) -> List[TranscriptTurn]:
        return self.transcript_manager.get_full_transcript(session_id)

    def get_state(self) -> Optional[GameState]:
        return self.state_store.state
