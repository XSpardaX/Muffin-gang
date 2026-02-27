"""Shared types and data models for the Muffin Gang Interrogation Game."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

CharacterId = Literal["Crumbs", "Cherry", "Glaze"]
ModelName = Literal["gemma3:4b", "qwen3:8b", "llama2-uncensored"]

CHARACTER_IDS: List[CharacterId] = ["Crumbs", "Cherry", "Glaze"]


@dataclass
class TranscriptTurn:
    """One turn in the interrogation (player question or NPC answer)."""
    session_id: str
    turn_id: int
    character_id: Optional[CharacterId]  # None for player-only turns
    speaker_type: Literal["PLAYER", "NPC"]
    timestamp: str
    player_question: Optional[str] = None
    raw_output: str = ""
    structured_claims: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "character_id": self.character_id,
            "speaker_type": self.speaker_type,
            "timestamp": self.timestamp,
            "player_question": self.player_question,
            "raw_output": self.raw_output,
            "structured_claims": self.structured_claims,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TranscriptTurn":
        return cls(
            session_id=d["session_id"],
            turn_id=d["turn_id"],
            character_id=d.get("character_id"),
            speaker_type=d["speaker_type"],
            timestamp=d["timestamp"],
            player_question=d.get("player_question"),
            raw_output=d.get("raw_output", ""),
            structured_claims=d.get("structured_claims", []),
            metadata=d.get("metadata", {}),
        )


@dataclass
class MemorySummary:
    """Per-character memory summary for prompt injection."""
    character_id: CharacterId
    core_alibi: str
    timeline_summary: str
    relationships_and_attitude: str
    key_claims: List[str]
    known_self_contradictions: List[str]
    known_inter_contradictions: List[str]
    lie_patterns: str
    last_updated_turn_id: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "core_alibi": self.core_alibi,
            "timeline_summary": self.timeline_summary,
            "relationships_and_attitude": self.relationships_and_attitude,
            "key_claims": self.key_claims,
            "known_self_contradictions": self.known_self_contradictions,
            "known_inter_contradictions": self.known_inter_contradictions,
            "lie_patterns": self.lie_patterns,
            "last_updated_turn_id": self.last_updated_turn_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MemorySummary":
        return cls(
            character_id=d["character_id"],
            core_alibi=d.get("core_alibi", ""),
            timeline_summary=d.get("timeline_summary", ""),
            relationships_and_attitude=d.get("relationships_and_attitude", ""),
            key_claims=d.get("key_claims", []),
            known_self_contradictions=d.get("known_self_contradictions", []),
            known_inter_contradictions=d.get("known_inter_contradictions", []),
            lie_patterns=d.get("lie_patterns", ""),
            last_updated_turn_id=d.get("last_updated_turn_id", 0),
        )


@dataclass
class Claim:
    """Structured claim extracted from an NPC statement."""
    subject: str
    action: str
    time: Optional[str] = None
    location: Optional[str] = None
    certainty: str = "stated"
    source_character_id: Optional[CharacterId] = None
    turn_id: int = 0


@dataclass
class Contradiction:
    """Detected contradiction between claims or within one character."""
    type: Literal["self", "inter_character"]
    character_id: CharacterId
    other_character_id: Optional[CharacterId] = None
    field: str = ""
    description: str = ""
    severity: Literal["low", "medium", "high"] = "medium"


@dataclass
class CharacterState:
    """Per-character game state."""
    character_id: CharacterId
    questions_remaining: int
    claims: List[Claim]
    suspicion_score: float
    contradictions: List[Contradiction]


@dataclass
class ScenarioCanon:
    """Canonical heist scenario (ground truth)."""
    guilty_character_id: CharacterId
    timeline: List[Dict[str, Any]]
    location: str
    key_events: List[str]
    who_saw_what: Dict[CharacterId, List[str]]


@dataclass
class GameState:
    """Full game state for a session."""
    session_id: str
    seed: int
    scenario: ScenarioCanon
    character_states: Dict[CharacterId, CharacterState]
    total_turns: int
    phase: Literal["intro", "interrogation", "review", "accusation", "ended"]
