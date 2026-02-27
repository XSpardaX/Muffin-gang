"""Central game state: scenario, character states, claims, contradictions, suspicion."""
import random
from typing import Dict, List, Optional

from .types import (
    CHARACTER_IDS,
    CharacterId,
    CharacterState,
    Claim,
    Contradiction,
    GameState,
    ScenarioCanon,
)
from typing import Literal

Phase = Literal["intro", "interrogation", "review", "accusation", "ended"]


def _make_default_canon(guilty_id: CharacterId, seed: int) -> ScenarioCanon:
    rng = random.Random(seed)
    locations = ["the bakery vault", "the back room", "the kitchen"]
    location = rng.choice(locations)
    return ScenarioCanon(
        guilty_character_id=guilty_id,
        timeline=[
            {"time": "20:00", "event": "Gang met at the bakery."},
            {"time": "21:00", "event": "Grand Muffin was taken from the vault."},
            {"time": "21:30", "event": "Someone left through the back."},
        ],
        location=location,
        key_events=["Meeting", "Vault opened", "Muffin removed", "Escape"],
        who_saw_what={
            "Crumbs": ["Saw Cherry near the kitchen.", "Did not see Glaze after 9pm."],
            "Cherry": ["Saw Glaze by the vault.", "Claims Crumbs was with them until 9."],
            "Glaze": ["Saw Cherry leave early.", "Claims to have been in the back room alone."],
        },
    )


class StateStore:
    """Holds and updates game state: scenario, character states, suspicion, contradictions."""

    def __init__(self, seed: Optional[int] = None) -> None:
        self._seed = seed if seed is not None else random.randint(0, 2**31 - 1)
        self._state: Optional[GameState] = None

    def initialize_session(self, session_id: str, questions_per_character: int = 2) -> GameState:
        rng = random.Random(self._seed)
        guilty_id = rng.choice(CHARACTER_IDS)
        scenario = _make_default_canon(guilty_id, self._seed)
        character_states = {
            cid: CharacterState(
                character_id=cid,
                questions_remaining=questions_per_character,
                claims=[],
                suspicion_score=0.0,
                contradictions=[],
            )
            for cid in CHARACTER_IDS
        }
        self._state = GameState(
            session_id=session_id,
            seed=self._seed,
            scenario=scenario,
            character_states=character_states,
            total_turns=0,
            phase="intro",
        )
        return self._state

    @property
    def state(self) -> Optional[GameState]:
        return self._state

    def get_guilty_character_id(self) -> Optional[CharacterId]:
        if not self._state:
            return None
        return self._state.scenario.guilty_character_id

    def get_character_state(self, character_id: CharacterId) -> Optional[CharacterState]:
        if not self._state:
            return None
        return self._state.character_states.get(character_id)

    def use_question(self, character_id: CharacterId) -> bool:
        if not self._state:
            return False
        cs = self._state.character_states.get(character_id)
        if not cs or cs.questions_remaining <= 0:
            return False
        cs.questions_remaining -= 1
        return True

    def add_claims(self, character_id: CharacterId, claims: List[Claim], turn_id: int) -> None:
        if not self._state:
            return
        for c in claims:
            c.source_character_id = character_id
            c.turn_id = turn_id
        self._state.character_states[character_id].claims.extend(claims)

    def add_contradiction(self, contradiction: Contradiction) -> None:
        if not self._state:
            return
        self._state.character_states[contradiction.character_id].contradictions.append(contradiction)

    def set_suspicion(self, character_id: CharacterId, score: float) -> None:
        if not self._state:
            return
        self._state.character_states[character_id].suspicion_score = max(0.0, min(100.0, score))

    def increment_turn(self) -> int:
        if not self._state:
            return 0
        self._state.total_turns += 1
        return self._state.total_turns

    def set_phase(self, phase: Phase) -> None:
        if self._state:
            self._state.phase = phase

    def get_suspicion_snapshot(self) -> Dict[CharacterId, float]:
        if not self._state:
            return {}
        return {cid: cs.suspicion_score for cid, cs in self._state.character_states.items()}

    def get_contradiction_notes_for_character(self, character_id: CharacterId) -> List[str]:
        if not self._state:
            return []
        cs = self._state.character_states.get(character_id)
        if not cs:
            return []
        return [c.description for c in cs.contradictions]
