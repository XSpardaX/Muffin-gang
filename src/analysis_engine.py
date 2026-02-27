"""Extracts claims from NPC text and updates suspicion/contradictions in StateStore."""
import re
from typing import List

from .state_store import StateStore
from .types import CharacterId, Claim, Contradiction, TranscriptTurn


def extract_claims_simple(raw_output: str, character_id: CharacterId, turn_id: int) -> List[Claim]:
    """Simple rule-based extraction: look for time/location/action patterns."""
    claims: List[Claim] = []
    time_match = re.search(r"\b(\d{1,2}[:\s]*\d{2}|\d{1,2}\s*(?:am|pm|o\'?clock))\b", raw_output, re.I)
    location_match = re.search(r"(?:at|in|near)\s+([^.?!]+?)(?:\.|,|$)", raw_output, re.I)
    if time_match:
        claims.append(
            Claim(
                subject=character_id,
                action="mentioned time",
                time=time_match.group(1).strip(),
                source_character_id=character_id,
                turn_id=turn_id,
            )
        )
    if location_match:
        claims.append(
            Claim(
                subject=character_id,
                action="mentioned location",
                location=location_match.group(1).strip(),
                source_character_id=character_id,
                turn_id=turn_id,
            )
        )
    if not claims:
        claims.append(
            Claim(
                subject=character_id,
                action=raw_output[:100] if len(raw_output) > 100 else raw_output,
                source_character_id=character_id,
                turn_id=turn_id,
            )
        )
    return claims


class AnalysisEngine:
    """Extracts claims, detects contradictions, updates suspicion in StateStore."""

    def __init__(self, state_store: StateStore) -> None:
        self.state_store = state_store

    def process_turn(self, turn: TranscriptTurn) -> None:
        if not turn.character_id or turn.speaker_type != "NPC":
            return
        state = self.state_store.state
        if not state:
            return
        claims = extract_claims_simple(turn.raw_output, turn.character_id, turn.turn_id)
        self.state_store.add_claims(turn.character_id, claims, turn.turn_id)
        self._check_contradictions(turn.character_id, claims)
        self._update_suspicion(turn.character_id)

    def _check_contradictions(self, character_id: CharacterId, new_claims: List[Claim]) -> None:
        state = self.state_store.state
        if not state:
            return
        guilty_id = state.scenario.guilty_character_id
        for other_id in state.character_states:
            if other_id == character_id:
                continue
            other_claims = state.character_states[other_id].claims
            for nc in new_claims:
                for oc in other_claims:
                    if nc.time and oc.time and nc.time != oc.time and nc.action == oc.action:
                        self.state_store.add_contradiction(
                            Contradiction(
                                type="inter_character",
                                character_id=character_id,
                                other_character_id=other_id,
                                field="time",
                                description=f"{character_id} said {nc.time}, {other_id} said {oc.time}.",
                                severity="medium",
                            )
                        )
                    if nc.location and oc.location and nc.location != oc.location:
                        self.state_store.add_contradiction(
                            Contradiction(
                                type="inter_character",
                                character_id=character_id,
                                other_character_id=other_id,
                                field="location",
                                description=f"{character_id} said {nc.location}, {other_id} said {oc.location}.",
                                severity="medium",
                            )
                        )
        existing = state.character_states[character_id].claims
        old_claims = existing[:-len(new_claims)] if len(new_claims) < len(existing) else []
        for nc in new_claims:
            for ec in old_claims:
                if nc.time and ec.time and nc.time != ec.time:
                    self.state_store.add_contradiction(
                        Contradiction(
                            type="self",
                            character_id=character_id,
                            field="time",
                            description=f"Previously said {ec.time}, now said {nc.time}.",
                            severity="high",
                        )
                    )

    def _update_suspicion(self, character_id: CharacterId) -> None:
        state = self.state_store.state
        if not state:
            return
        cs = state.character_states[character_id]
        base = len(cs.contradictions) * 15.0
        if state.scenario.guilty_character_id == character_id:
            base += 10.0
        self.state_store.set_suspicion(character_id, min(100.0, cs.suspicion_score + base))
