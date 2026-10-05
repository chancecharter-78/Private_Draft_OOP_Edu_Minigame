import time

import streamlit as st


def start_timer(game_key="default"):
    st.session_state[f"{game_key}_start_time"] = time.monotonic()
    st.session_state[f"{game_key}_is_active"] = True
    st.session_state[f"{game_key}_elapsed"] = 0.0


def stop_timer(game_key="default"):
    if st.session_state.get(f"{game_key}_is_active", False):
        elapsed = get_elapsed(game_key)
        st.session_state[f"{game_key}_elapsed"] = elapsed
        st.session_state[f"{game_key}_is_active"] = False
        return elapsed
    return st.session_state.get(f"{game_key}_elapsed", 0.0)


def get_elapsed(game_key="default"):
    if st.session_state.get(f"{game_key}_is_active", False):
        start_time = st.session_state.get(f"{game_key}_start_time", time.monotonic())
        return time.monotonic() - start_time
    return st.session_state.get(f"{game_key}_elapsed", 0.0)


def format_time(seconds):
    tenths_total = round(max(0, seconds) * 10)
    minutes, remaining_tenths = divmod(tenths_total, 600)
    whole_seconds, tenths = divmod(remaining_tenths, 10)
    return f"{minutes:02d}:{whole_seconds:02d}.{tenths}"


def render_timer_display(game_key="default", label="Time Elapsed"):
    run_every = 0.1 if st.session_state.get(f"{game_key}_is_active", False) else None

    @st.fragment(run_every=run_every)
    def draw():
        st.metric(label=label, value=format_time(get_elapsed(game_key)))

    draw()
