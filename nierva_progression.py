import random

import streamlit as st


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
    "set",
    "nav_game",
    "username",
    "save_data",
    "flow_game",
    "flow_clears",
    "flow_target",
    "switch_message",
}


def start_game(game_name, message=""):
    if game_name not in GAME_ORDER:
        return

    for key in list(st.session_state.keys()):
        if key not in _SHARED_SESSION_KEYS:
            del st.session_state[key]

    st.session_state.page = game_name
    st.session_state.set = game_name
    st.session_state.project = True
    st.session_state.game = True
    st.session_state.flow_game = game_name
    st.session_state.flow_clears = 0
    st.session_state.flow_target = random.randint(*GAME_CLEAR_RANGES[game_name])
    st.session_state.switch_message = message


def reset_game(game_name):
    start_game(game_name)


def record_success(game_name, success_message=""):
    if st.session_state.get("flow_game") != game_name:
        start_game(game_name)

    st.session_state.flow_clears += 1
    if st.session_state.flow_clears < st.session_state.flow_target:
        return False

    next_games = [name for name in GAME_ORDER if name != game_name]
    next_game = random.choice(next_games)
    message = f"{success_message} Switching to {next_game}...".strip()
    start_game(next_game, message)
    return True


def finish_game(game_name, message):
    next_games = [name for name in GAME_ORDER if name != game_name]
    next_game = random.choice(next_games)
    start_game(next_game, f"{message} Switching to {next_game}...")


def record_failure(game_name):
    st.session_state.flow_game = game_name
    st.session_state.flow_clears = 0
    st.session_state.flow_target = random.randint(*GAME_CLEAR_RANGES[game_name])
