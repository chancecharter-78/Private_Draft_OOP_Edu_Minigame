import random
import time
from html import escape

import streamlit as st

import nierva_combo_system
import nierva_progression
import nierva_timer
from nierva_save_data import ensure_current_save_data


TOTAL_SLIDERS = 5
MINIMUM_WINS = TOTAL_SLIDERS // 2 + 1
SLIDER_REFRESH_SECONDS = 0.2
SLIDER_STATE_KEYS = (
    "slider_level",
    "slider_wins",
    "slider_history",
    "slider_total_elapsed",
    "slider_position",
    "slider_direction",
    "slider_over",
    "slider_msg",
    "slider_last_update",
    "slider_pending_initial_start",
    "slider_position_history",
    "slider_question",
    "slider_choices",
    "slider_correct_index",
    "slider_round_locked",
)


def reset_slider_timer():
    nierva_timer.start_timer("slider")
    st.session_state.slider_last_update = time.monotonic()
    st.session_state.slider_over = False


def get_save_data():
    st.session_state.save_data = ensure_current_save_data(
        st.session_state.get("save_data")
    )
    return st.session_state.save_data


def slider_state_initialized():
    return all(key in st.session_state for key in SLIDER_STATE_KEYS)


def init_slider():
    st.session_state.slider_level = 1
    st.session_state.slider_wins = 0
    st.session_state.slider_history = []
    st.session_state.slider_total_elapsed = 0.0
    st.session_state.slider_position = 50
    st.session_state.slider_direction = 1
    st.session_state.slider_over = False
    st.session_state.slider_msg = ""
    st.session_state.slider_last_update = time.monotonic()
    st.session_state.slider_pending_initial_start = True
    st.session_state.slider_position_history = []
    st.session_state.slider_round_locked = False
    set_slider_question()


def set_slider_question():
    previous_question = st.session_state.get("slider_question", {}).get("question")
    question = get_save_data().get_random_question(previous_question)
    choices = [question["correct_answer"], *question["wrong_answers"]]
    random.shuffle(choices)

    st.session_state.slider_question = question
    st.session_state.slider_choices = choices
    st.session_state.slider_correct_index = choices.index(question["correct_answer"])
    st.session_state.slider_position_history = []


def advance_position(position, direction, speed, elapsed):
    phase = position if direction > 0 else 200 - position
    phase = (phase + speed * 10 * elapsed) % 200
    if phase < 100:
        return phase, 1
    return 200 - phase, -1


def get_stop_position(history):
    if not history:
        return None
    return history[-1]


def is_position_within_correct_zone(position, correct_index, tick_grace):
    zone_start = correct_index * 25
    zone_end = (correct_index + 1) * 25
    return (
        max(0, zone_start - tick_grace)
        <= position
        <= min(100, zone_end + tick_grace)
    )


def update_marker():
    history = st.session_state.setdefault("slider_position_history", [])
    now = time.monotonic()
    previous_update = st.session_state.get("slider_last_update", now)
    elapsed = now - previous_update
    st.session_state.slider_last_update = now

    if st.session_state.get("slider_over", True):
        return

    speed = 2 + st.session_state.slider_level * 2
    position, direction = advance_position(
        st.session_state.slider_position,
        st.session_state.slider_direction,
        speed,
        elapsed,
    )
    st.session_state.slider_position = position
    st.session_state.slider_direction = direction
    history.append((position, direction))
    st.session_state.slider_position_history = history[-3:]


def end_slider():
    elapsed = st.session_state.slider_total_elapsed
    if st.session_state.slider_wins >= MINIMUM_WINS:
        message = (
            f"🎉 You cleared {st.session_state.slider_wins} of {TOTAL_SLIDERS} sliders "
            f"in {nierva_timer.format_time(elapsed)}!"
        )
        st.session_state.slider_over = True
        st.session_state.slider_completed_summary = {
            "won": True,
            "message": message,
            "history": list(st.session_state.slider_history),
            "score": get_save_data().check_score(),
            "timer": nierva_timer.format_time(elapsed),
        }
        nierva_progression.finish_game("Slider", message)
        return

    st.session_state.slider_over = True
    st.session_state.slider_msg = (
        f"❌ You cleared {st.session_state.slider_wins} of {TOTAL_SLIDERS} sliders. "
        f"You needed {MINIMUM_WINS} to continue. "
        f"Game over after {nierva_timer.format_time(elapsed)}."
    )
    st.session_state.slider_completed_summary = {
        "won": False,
        "message": st.session_state.slider_msg,
        "history": list(st.session_state.slider_history),
        "score": get_save_data().check_score(),
        "timer": nierva_timer.format_time(elapsed),
    }
    nierva_progression.record_failure("Slider", st.session_state.slider_msg)


def finish_round(won, selected_index=None):
    level = st.session_state.slider_level
    question = st.session_state.slider_question
    choices = st.session_state.slider_choices
    position = st.session_state.slider_position
    elapsed = nierva_timer.get_elapsed("slider")
    nierva_timer.stop_timer("slider")
    st.session_state.slider_total_elapsed += elapsed
    if selected_index is None:
        selected_index = min(int(position // 25), 3)
    selected_answer = choices[selected_index]
    correct_answer = question["correct_answer"]
    automated_rating = nierva_progression.record_question_result(
        question,
        selected_answer,
        won,
        elapsed,
        nierva_progression.QUESTION_TARGET_SECONDS["Slider"],
    )
    st.session_state.slider_history.append({
        "level": level,
        "question": question["question"],
        "choices": choices,
        "position": position,
        "won": won,
        "selected_answer": selected_answer,
        "correct_answer": correct_answer,
        "selected_index": selected_index,
        "correct_index": st.session_state.slider_correct_index,
        "elapsed_seconds": elapsed,
        "automated_rating": automated_rating,
    })

    if won:
        answer = choices[st.session_state.slider_correct_index]
        reward = nierva_combo_system.apply_win(
            "Slider",
            elapsed_seconds=elapsed,
            correct_questions=st.session_state.slider_wins + 1,
        )
        get_save_data().record_clear(
            "Slider Minigame",
            level,
            f"Answered {answer} at {position:.1f}%",
            points=reward["final_points"],
        )
        st.session_state.slider_wins += 1
        st.session_state.slider_msg = f"✅ Correct! Level {level} cleared."
    else:
        nierva_combo_system.apply_soft_fail("Slider")
        st.session_state.slider_msg = (
            f"❌ Incorrect choice. The answer was {question['correct_answer']}."
        )

    if level >= TOTAL_SLIDERS:
        end_slider()
        return

    st.session_state.slider_level += 1
    st.session_state.slider_position = 50
    st.session_state.slider_direction = 1
    set_slider_question()
    st.session_state.slider_round_locked = False
    reset_slider_timer()


def lock_slider():
    if (
        st.session_state.slider_over
        or st.session_state.get("slider_round_locked", False)
    ):
        return
    st.session_state.slider_round_locked = True
    history = st.session_state.get("slider_position_history", [])
    latest_tick = get_stop_position(history)
    if latest_tick is not None:
        position, direction = latest_tick
        st.session_state.slider_position = position
        st.session_state.slider_direction = direction
    selected_index = min(int(st.session_state.slider_position // 25), 3)
    correct_index = st.session_state.slider_correct_index
    tick_grace = (
        abs(history[-1][0] - history[-2][0])
        if len(history) > 1
        else 0
    )
    within_grace = is_position_within_correct_zone(
        st.session_state.slider_position,
        correct_index,
        tick_grace,
    )
    if selected_index == correct_index:
        finish_round(True)
    elif within_grace:
        finish_round(True, selected_index=correct_index)
    else:
        finish_round(False)


def render_slider_bar(choices, position):
    choice_boxes = "".join(
        "<div style='display:flex;align-items:center;justify-content:center;"
        "position:relative;min-width:0;min-height:72px;padding:6px;"
        "border:2px solid #697586;background:#202a36;color:#fff;"
        "text-align:center;overflow-wrap:anywhere;font-weight:600;'>"
        f"{escape(choice)}</div>"
        for choice in choices
    )
    st.markdown(
        f"""
        <div style="position:relative;display:grid;
            grid-template-columns:repeat(4,minmax(0,1fr));width:100%;margin:15px 0 28px;">
            {choice_boxes}
            <div style="position:absolute;z-index:3;left:{position}%;top:-9px;
                width:5px;height:88px;background:#f6c453;border:1px solid #202020;
                transform:translateX(-50%);"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.fragment(run_every=SLIDER_REFRESH_SECONDS)
def render_active_slider():
    update_marker()
    st.metric("Game Time", nierva_timer.format_time(nierva_timer.get_elapsed("slider")))
    nierva_combo_system.render_combo_status("Combo", visible=False)
    render_slider_bar(
        st.session_state.slider_choices,
        st.session_state.slider_position,
    )


def render_game_over():
    nierva_progression.render_game_result("Slider", get_save_data())


def main():
    st.write("# 🎚️ Slider Minigame")
    st.caption("Answer each question by stopping the marker over the correct choice.")

    save_data = get_save_data()
    if not slider_state_initialized():
        init_slider()

    if st.session_state.get("game_result_ready", False):
        render_game_over()
        return
    if not nierva_progression.render_start_gate("Slider", "slider"):
        return
    if st.session_state.get("slider_pending_initial_start", False):
        st.session_state.slider_last_update = time.monotonic()
        st.session_state.slider_pending_initial_start = False

    level_col, score_col, new_game_col = st.columns([1, 1, 1])
    level_col.metric("Level", f"{st.session_state.slider_level}/{TOTAL_SLIDERS}")
    score_col.metric("Saved Score", save_data.check_score())
    new_game_col.button(
        "New Game",
        key="slider_new_game_top",
        on_click=nierva_progression.start_game,
        args=("Slider",),
    )

    if not st.session_state.slider_over:
        level = st.session_state.slider_level
        question = st.session_state.slider_question
        st.caption(f"Current Level {level}")
        st.info(question["question"])
        st.caption(
            f"Subject: {question['game']} | Difficulty: {question['difficulty']}"
        )
        st.button(
            "🛑 STOP SLIDER (LMB)",
            key=f"slider_stop_button_{level}",
            on_click=lock_slider,
            width="stretch",
        )
        render_active_slider()
        if st.session_state.slider_msg:
            st.success(st.session_state.slider_msg)
    else:
        render_game_over()


if __name__ == "__main__":
    main()
