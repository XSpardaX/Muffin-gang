# Muffin Gang Interrogation Game

A narrative-driven text interrogation game where you question three gang members (Crumbs, Cherry, Glaze) to find who stole the Grand Muffin. Each character is powered by a different Ollama model.

## Requirements

- Python 3.8+
- [Ollama](https://ollama.ai) installed and running with these models pulled:
  - `gemma3:4b` (Crumbs)
  - `qwen3:8b` (Cherry)
  - `llama2-uncensored` (Glaze)

## Setup

```bash
pip install -r requirements.txt
ollama pull gemma3:4b
ollama pull qwen3:8b
ollama pull llama2-uncensored
```

## Run

```bash
python main.py
```

You get 2 questions per character. Ask questions, then accuse one of the three. The game tracks statements, contradictions, and suspicion internally.

## Project layout

- `main.py` – CLI entry point
- `src/` – Core modules:
  - `types.py` – Data models
  - `config.py` – Character personas and model mapping
  - `transcript_manager.py` – Circular buffer of transcript files (per character)
  - `memory_manager.py` – Per-character memory summaries
  - `character_agent.py` – One character + Ollama model, prompt building
  - `ai_manager.py` – Routes questions to the right character agent
  - `state_store.py` – Game state, guilt, suspicion, claims
  - `analysis_engine.py` – Claim extraction and contradiction detection
  - `game_orchestrator.py` – Session start, ask, accuse
- `transcripts/` – Session transcript files (created at runtime)
- `session_data/` – Memory summaries and session data (created at runtime)
