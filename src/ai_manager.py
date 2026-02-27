"""Orchestrates AI: character agents, model routing, and integration with memory/transcript."""
import time
from typing import Dict, List, Optional

from .character_agent import CharacterAgent
from .config import MODEL_MAP, PERSONA_SYSTEM_PROMPTS
from .memory_manager import MemoryManager
from .transcript_manager import TranscriptManager
from .types import CHARACTER_IDS, CharacterId, GameState, TranscriptTurn


class AIManager:
    """Spin-up, routing, prompt reconstruction, response retrieval; integrates Memory and Transcript."""

    def __init__(
        self,
        memory_manager: MemoryManager,
        transcript_manager: TranscriptManager,
        model_map: Optional[Dict[CharacterId, str]] = None,
    ) -> None:
        self.memory_manager = memory_manager
        self.transcript_manager = transcript_manager
        self.model_map = model_map or MODEL_MAP
        self._agents: Dict[CharacterId, CharacterAgent] = {}
        self._game_state: Optional[GameState] = None

    def set_game_state(self, state: GameState) -> None:
        """Inject current game state so AIManager knows who is guilty and can pass contradiction notes."""
        self._game_state = state

    def initialize_session(self, session_id: str, guilty_character_id: CharacterId) -> None:
        for cid in CHARACTER_IDS:
            guilty = cid == guilty_character_id
            agent = CharacterAgent(
                character_id=cid,
                model_name=self.model_map[cid],
                persona_system_prompt=PERSONA_SYSTEM_PROMPTS[cid],
                guilty=guilty,
                memory_manager=self.memory_manager,
                transcript_manager=self.transcript_manager,
            )
            self._agents[cid] = agent

    def get_character_agent(self, character_id: CharacterId) -> CharacterAgent:
        return self._agents[character_id]

    def ask_character(
        self,
        session_id: str,
        character_id: CharacterId,
        turn_id: int,
        player_question: str,
        suspicion_snapshot: Optional[Dict[CharacterId, float]] = None,
        contradictions_for_character: Optional[List[str]] = None,
    ) -> TranscriptTurn:
        agent = self.get_character_agent(character_id)
        recent_turns = self.transcript_manager.get_character_last_n_turns(session_id, character_id, 5)
        summary = self.memory_manager.load_memory_summary(session_id, character_id)
        contradiction_notes = contradictions_for_character or []

        raw_output = agent.answer_question(
            session_id=session_id,
            turn_id=turn_id,
            player_question=player_question,
            memory_summary=summary,
            recent_turns=recent_turns,
            contradiction_notes=contradiction_notes,
        )

        turn = TranscriptTurn(
            session_id=session_id,
            turn_id=turn_id,
            character_id=character_id,
            speaker_type="NPC",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            player_question=player_question,
            raw_output=raw_output,
            structured_claims=[],
            metadata={"suspicion_snapshot": suspicion_snapshot or {}},
        )
        self.transcript_manager.log_turn(session_id, character_id, turn)
        all_turns = self.transcript_manager.get_character_turns(session_id, character_id)
        self.memory_manager.maybe_summarize_character(session_id, character_id, all_turns)
        return turn

    def shutdown_session(self, session_id: str) -> None:
        self._game_state = None
