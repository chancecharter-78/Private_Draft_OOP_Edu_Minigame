import random
import time

import streamlit as st

import nierva_spaced_repetition
import nierva_timer


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
    "review_history",
    "game_result_ready",
    "game_next_game",
    "game_start_started_at",
    "game_start_active",
    "game_start_last_toast",
    "review_user_rating",
    "review_saved",
}
START_DELAY_SECONDS = 3
COUNTDOWN_SECONDS = 3
RATING_LABELS = {
    1: "Again",
    2: "Hard",
    3: "Good",
    4: "Easy",
}
QUESTION_TARGET_SECONDS = {
    "Slider": 8.0,
    "Bit Fit": 10.0,
    "Hacking": 8.0,
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
    st.session_state.review_history = []
    st.session_state.game_result_ready = False
    st.session_state.game_next_game = None
    st.session_state.game_start_started_at = None
    st.session_state.game_start_active = False
    st.session_state.game_start_last_toast = None
    st.session_state.review_user_rating = 3
    st.session_state.review_saved = False


def reset_game(game_name):
    start_game(game_name)


@st.fragment(run_every=0.2)
def render_start_gate(game_name, timer_key):
    if st.session_state.get("game_start_active", False):
        return True

    started_at = st.session_state.get("game_start_started_at")
    if started_at is None:
        started_at = time.monotonic()
        st.session_state.game_start_started_at = started_at
    elapsed = time.monotonic() - started_at
    phase, countdown = get_start_phase(elapsed)
    if phase == "delay":
        st.info("Get ready…")
        return False

    if phase == "countdown":
        st.markdown(f"## {countdown}")
        if st.session_state.get("game_start_last_toast") != countdown:
            st.toast(f"{game_name} starts in {countdown}…", icon="⏳")
            st.session_state.game_start_last_toast = countdown
        return False

    st.session_state.game_start_active = True
    nierva_timer.start_timer(timer_key)
    st.rerun()
    return True


def get_start_phase(elapsed):
    if elapsed < START_DELAY_SECONDS:
        return "delay", None
    countdown_elapsed = elapsed - START_DELAY_SECONDS
    if countdown_elapsed < COUNTDOWN_SECONDS:
        return "countdown", COUNTDOWN_SECONDS - int(countdown_elapsed)
    return "ready", None


def record_question_result(question, chosen_answer, won, elapsed_seconds, target_seconds):
    automated_rating = nierva_spaced_repetition.map_performance_to_rating(
        won,
        elapsed_seconds,
        target_seconds,
    )
    st.session_state.setdefault("review_history", []).append({
        "question": question["question"],
        "chosen_answer": chosen_answer,
        "correct_answer": question["correct_answer"],
        "won": won,
        "elapsed_seconds": elapsed_seconds,
        "automated_rating": automated_rating,
    })
    return automated_rating


def finish_game(game_name, message):
    next_games = [name for name in GAME_ORDER if name != game_name]
    st.session_state.game_result_ready = True
    st.session_state.game_next_game = random.choice(next_games)
    st.session_state.game_result_message = message
    st.session_state.game_start_active = False


def record_failure(game_name, message=""):
    st.session_state.flow_game = game_name
    st.session_state.flow_clears = 0
    st.session_state.flow_target = random.randint(*GAME_CLEAR_RANGES[game_name])
    finish_game(game_name, message)


def record_success(game_name, success_message=""):
    if st.session_state.get("flow_game") != game_name:
        start_game(game_name)

    st.session_state.flow_clears += 1
    if st.session_state.flow_clears < st.session_state.flow_target:
        return False

    finish_game(game_name, success_message)
    return True


def render_game_result(game_name, save_data):
    st.subheader("Game results")
    message = st.session_state.get("game_result_message", "")
    if message:
        st.info(message)

    history = st.session_state.get("review_history", [])
    if history:
        rating_names = RATING_LABELS
        rows = []
        for result in history:
            final_rating = nierva_spaced_repetition.combine_ratings(
                result["automated_rating"],
                st.session_state.get("review_user_rating", 3),
            )
            rows.append({
                "Question": result["question"],
                "Your answer": result["chosen_answer"],
                "Correct answer": result["correct_answer"],
                "Time (s)": round(result["elapsed_seconds"], 1),
                "Automatic": rating_names[result["automated_rating"]],
                "Final": rating_names[final_rating],
            })
        st.dataframe(rows, hide_index=True, width="stretch")

        st.selectbox(
            "Rate your performance for this game",
            options=tuple(RATING_LABELS),
            format_func=lambda rating: RATING_LABELS[rating],
            key="review_user_rating",
        )
        st.button(
            "Save rating and Continue",
            key=f"{game_name}_save_rating",
            on_click=save_rating_and_continue,
            args=(game_name, save_data),
        )
        return

    st.button(
        "Continue",
        key=f"{game_name}_continue",
        on_click=continue_to_next_game,
        args=(game_name,),
    )


def save_rating_and_continue(game_name, save_data):
    user_rating = st.session_state.review_user_rating
    for result in st.session_state.get("review_history", []):
        final_rating = nierva_spaced_repetition.combine_ratings(
            result["automated_rating"],
            user_rating,
        )
        save_data.record_question_review(result["question"], final_rating)
    continue_to_next_game(game_name)


def continue_to_next_game(game_name):
    next_game = st.session_state.get("game_next_game")
    if next_game not in GAME_ORDER:
        next_game = random.choice([name for name in GAME_ORDER if name != game_name])
    start_game(next_game)
