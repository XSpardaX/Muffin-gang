"""Single gang member bound to an Ollama model; builds prompts and calls the model."""
from typing import TYPE_CHECKING, List

from .config import PERSONA_SYSTEM_PROMPTS, get_hidden_instructions
from .types import CharacterId, MemorySummary, ModelName, TranscriptTurn

if TYPE_CHECKING:
    from .memory_manager import MemoryManager
    from .transcript_manager import TranscriptManager

try:
    import ollama
except ImportError:
    ollama = None


class CharacterAgent:
    """One gang member: persona, model, and prompt construction."""

    def __init__(
        self,
        character_id: CharacterId,
        model_name: ModelName,
        persona_system_prompt: str,
        guilty: bool,
        memory_manager: "MemoryManager",
        transcript_manager: "TranscriptManager",
    ) -> None:
        self.character_id = character_id
        self.model_name = model_name
        self.persona_system_prompt = persona_system_prompt
        self.guilty = guilty
        self.memory_manager = memory_manager
        self.transcript_manager = transcript_manager

    def build_prompt(
        self,
        session_id: str,
        turn_id: int,
        player_question: str,
        memory_summary: MemorySummary,
        recent_turns: List[TranscriptTurn],
        contradiction_notes: List[str],
    ) -> str:
        parts = [
            "--- MEMORY RECAP ---",
            f"Your key claims so far: {memory_summary.key_claims or ['None yet.']}",
            f"Your alibi / story: {memory_summary.core_alibi or 'Not yet stated.'}",
        ]
        if contradiction_notes:
            parts.append("Contradictions to be aware of (stay consistent or address carefully):")
            for n in contradiction_notes[:5]:
                parts.append(f"  - {n}")
        if recent_turns:
            parts.append("\n--- YOUR RECENT ANSWERS ---")
            for t in recent_turns[-5:]:
                if t.player_question:
                    parts.append(f"Investigator asked: {t.player_question[:200]}")
                parts.append(f"You said: {t.raw_output[:300]}")
        parts.append("\n--- NEW QUESTION ---")
        parts.append(f"The investigator asks: {player_question}")
        parts.append("\nReply in character only, in 1-3 short paragraphs. Do not confess or break character.")
        return "\n".join(parts)

    def call_model(self, prompt: str) -> str:
        if ollama is None:
            return "[Ollama not installed. Install with: pip install ollama]"
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.persona_system_prompt + "\n\n" + get_hidden_instructions(self.guilty)},
                    {"role": "user", "content": prompt},
                ],
            )
            msg = response.get("message") or {}
            return (msg.get("content") or "").strip()
        except Exception as e:
            return f"[Error calling model: {e}]"

    def answer_question(
        self,
        session_id: str,
        turn_id: int,
        player_question: str,
        memory_summary: MemorySummary,
        recent_turns: List[TranscriptTurn],
        contradiction_notes: List[str],
    ) -> str:
        prompt = self.build_prompt(
            session_id=session_id,
            turn_id=turn_id,
            player_question=player_question,
            memory_summary=memory_summary,
            recent_turns=recent_turns,
            contradiction_notes=contradiction_notes,
        )
        return self.call_model(prompt)
