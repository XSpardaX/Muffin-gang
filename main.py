#!/usr/bin/env python3
"""CLI entry point for the Muffin Gang Interrogation Game."""
import sys
from pathlib import Path
from typing import cast

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.game_orchestrator import GameOrchestrator
from src.types import CHARACTER_IDS, CharacterId


def main() -> None:
    orch = GameOrchestrator()
    session_id, intro, state = orch.start_game(questions_per_character=2)
    print(intro)
    print()

    while True:
        state = orch.get_state()
        if not state or state.phase != "interrogation":
            break
        remaining = {cid: state.character_states[cid].questions_remaining for cid in CHARACTER_IDS}
        if all(remaining[cid] == 0 for cid in CHARACTER_IDS):
            print("You have no questions left. Time to accuse.")
            break

        print("Questions left:", ", ".join(f"{c}: {remaining[c]}" for c in CHARACTER_IDS))
        print("Choose who to question: 1=Crumbs, 2=Cherry, 3=Glaze, 0=Accuse now")
        choice = input("> ").strip()
        if choice == "0":
            break
        idx = {"1": "Crumbs", "2": "Cherry", "3": "Glaze"}.get(choice)
        if idx is None or idx not in CHARACTER_IDS:
            print("Invalid choice.")
            continue
        character_id: CharacterId = idx
        if not orch.can_ask(character_id):
            print(f"No questions left for {character_id}.")
            continue
        question = input(f"Your question for {character_id}: ").strip()
        if not question:
            print("Ask something.")
            continue
        turn = orch.ask(session_id, character_id, question)
        if turn:
            print(f"\n{character_id}: {turn.raw_output}\n")
        else:
            print("Could not process that question.")

    print("\nWho do you accuse? 1=Crumbs, 2=Cherry, 3=Glaze")
    acc = input("> ").strip()
    accused = {"1": "Crumbs", "2": "Cherry", "3": "Glaze"}.get(acc)
    if accused not in CHARACTER_IDS:
        print("Invalid. Exiting.")
        return
    correct, reveal = orch.accuse(session_id, cast(CharacterId, accused))
    print(reveal)
    print("You win!" if correct else "You lose.")


if __name__ == "__main__":
    main()
