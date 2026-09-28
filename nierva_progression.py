import streamlit as st
import random

GAME_ORDER = ("Slider", "Bit Fit", "Hacking")
GAME_CLEAR_RANGES = {
    "Slider": (2, 6),
    "Bit Fit": (5, 8),
    "Hacking": (4, 6),
}

_SHARED_SESSION_KEYS = {
    "page",
    "project",
    "game",
    "pages",
    "set",
    "save_data",
    "nierva_save_data",
    "flow_game",
    "flow_clears",
    "flow_target",
}


def start_game(game_name: str) -> None:
    if game_name not in GAME_CLEAR_RANGES:
        return

    for key in list(st.session_state.keys()):
        if key not in _SHARED_SESSION_KEYS:
            st.session_state.pop(key)

    st.session_state.page = game_name
    st.session_state.set = game_name
    st.session_state.project = True
    st.session_state.game = True
    st.session_state.flow_game = game_name
    st.session_state.flow_clears = 0
    st.session_state.flow_target = random.randint(*GAME_CLEAR_RANGES[game_name])


def record_success(game_name: str) -> bool:
    if st.session_state.get("flow_game") != game_name:
        start_game(game_name)

    st.session_state.flow_clears += 1
    if st.session_state.flow_clears < st.session_state.flow_target:
        return False

    next_index = (GAME_ORDER.index(game_name) + 1) % len(GAME_ORDER)
    start_game(GAME_ORDER[next_index])
    return True
