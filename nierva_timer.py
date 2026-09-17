import streamlit as st
import time

def start_timer(game_key: str = "default"):
    st.session_state[f"{game_key}_start_time"] = time.time()
    st.session_state[f"{game_key}_is_active"] = True
    st.session_state[f"{game_key}_elapsed"] = 0.0

def stop_timer(game_key: str = "default") -> float:
    if f"{game_key}_start_time" in st.session_state and st.session_state.get(f"{game_key}_is_active", False):
        elapsed = time.time() - st.session_state[f"{game_key}_start_time"]
        st.session_state[f"{game_key}_elapsed"] = elapsed
        st.session_state[f"{game_key}_is_active"] = False
        return elapsed
    return st.session_state.get(f"{game_key}_elapsed", 0.0)

def get_elapsed(game_key: str = "default") -> float:
    if st.session_state.get(f"{game_key}_is_active", False):
        return time.time() - st.session_state.get(f"{game_key}_start_time", time.time())
    return st.session_state.get(f"{game_key}_elapsed", 0.0)

def format_time(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    tenths = int((seconds - int(seconds)) * 10)
    return f"{mins:02d}:{secs:02d}.{tenths}"

@st.fragment(run_every=1.0)
def render_timer_display(game_key: str = "default", label: str = "Time Elapsed"):
    elapsed = get_elapsed(game_key)
    st.metric(label=label, value=format_time(elapsed))
