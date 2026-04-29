import streamlit as st

from src.game_orchestrator import GameOrchestrator
from src.types import CHARACTER_IDS, CharacterId

CHARACTER_IMAGE_PATHS: dict[CharacterId, str] = {
    "Crumbs": "images/Crumbs.png",
    "Cherry": "images/Cherry.png",
    "Glaze": "images/Glaze.png",
}
PLAYER_IMAGE_PATH = "images/Muffin man.png"


def _get_orchestrator() -> GameOrchestrator:
    orch = st.session_state.get("orch")
    if orch is None:
        orch = GameOrchestrator()
        st.session_state["orch"] = orch
    return orch


def _start_new_game(questions_per_character: int) -> None:
    orch = _get_orchestrator()
    session_id, intro, _state = orch.start_game(questions_per_character=questions_per_character)
    st.session_state["session_id"] = session_id
    st.session_state["intro"] = intro
    st.session_state["last_turn_error"] = None
    st.session_state["accusation_result"] = None


st.set_page_config(page_title="Muffin Gang Interrogation", page_icon="🧁", layout="centered")
st.title("Muffin Gang Interrogation Game")

with st.sidebar:
    st.header("Game")
    st.image(PLAYER_IMAGE_PATH, caption="Muffin Man (You)", use_container_width=True)
    qpc = st.number_input("Questions per character", min_value=1, max_value=10, value=2, step=1)
    if st.button("Start / Restart game", type="primary"):
        _start_new_game(int(qpc))

orch = _get_orchestrator()
session_id = st.session_state.get("session_id")

if not session_id:
    st.info("Click **Start / Restart game** in the sidebar to begin.")
    st.stop()

intro = st.session_state.get("intro")
if intro:
    st.write(intro)

state = orch.get_state()
if not state:
    st.warning("No active game state. Restart the game from the sidebar.")
    st.stop()

remaining = {cid: state.character_states[cid].questions_remaining for cid in CHARACTER_IDS}

st.subheader("Questions remaining")
cols = st.columns(3)
for i, cid in enumerate(CHARACTER_IDS):
    with cols[i]:
        st.image(CHARACTER_IMAGE_PATHS[cid], caption=cid, use_container_width=True)
        st.metric("Questions", remaining[cid])

st.subheader("Ask a question")
character_id = st.selectbox("Choose a character", options=list(CHARACTER_IDS))
st.image(CHARACTER_IMAGE_PATHS[character_id], use_container_width=True)
question = st.text_input("Your question", placeholder="Ask about alibis, timing, motives…")

ask_disabled = (state.phase != "interrogation") or (remaining[character_id] <= 0) or not question.strip()
if st.button("Ask", disabled=ask_disabled):
    st.session_state["last_turn_error"] = None
    try:
        turn = orch.ask(session_id, character_id, question.strip())
        if not turn:
            st.session_state["last_turn_error"] = "Could not process that question."
        else:
            st.session_state["last_turn_error"] = None
    except Exception as e:
        st.session_state["last_turn_error"] = str(e)
    st.rerun()

last_err = st.session_state.get("last_turn_error")
if last_err:
    st.error(last_err)

st.subheader("Transcript")
turns = orch.get_full_transcript(session_id)
if not turns:
    st.caption("No turns yet.")
else:
    for t in turns[-30:]:
        if t.player_question:
            st.markdown(f"**You → {t.character_id}:** {t.player_question}")
        c1, c2 = st.columns([1, 4], vertical_alignment="top")
        with c1:
            st.image(CHARACTER_IMAGE_PATHS[t.character_id], use_container_width=True)
        with c2:
            st.markdown(f"**{t.character_id}:** {t.raw_output}")
        st.divider()

st.subheader("Accuse")
accused: CharacterId = st.selectbox("Who stole the Grand Muffin?", options=list(CHARACTER_IDS), key="accused")

accuse_disabled = state.phase == "ended"
if st.button("Accuse", type="secondary", disabled=accuse_disabled):
    correct, reveal = orch.accuse(session_id, accused)
    st.session_state["accusation_result"] = (correct, reveal)
    st.rerun()

acc_res = st.session_state.get("accusation_result")
if acc_res:
    correct, reveal = acc_res
    (st.success if correct else st.error)(reveal)
