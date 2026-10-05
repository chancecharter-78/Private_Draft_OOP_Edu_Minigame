import random
import time
from html import escape

import streamlit as st

import nierva_progression
import nierva_timer
from nierva_save_data import ensure_current_save_data


TOTAL_SLIDERS = 5
SLIDER_TIMES = (15, 12, 12, 8, 8)
MINIMUM_WINS = TOTAL_SLIDERS // 2 + 1


def get_save_data():
    st.session_state.save_data = ensure_current_save_data(
        st.session_state.get("save_data")
    )
    return st.session_state.save_data


def init_slider():
    nierva_progression.reset_game("Slider")
    st.session_state.slider_level = 1
    st.session_state.slider_wins = 0
    st.session_state.slider_history = []
    st.session_state.slider_position = 50
    st.session_state.slider_direction = 1
    st.session_state.slider_over = False
    st.session_state.slider_msg = ""
    nierva_timer.start_timer("slider")
    set_slider_question()


def set_slider_question():
    previous_question = st.session_state.get("slider_question", {}).get("question")
    question = get_save_data().get_random_question(previous_question)
    choices = [question["correct_answer"], *question["wrong_answers"]]
    random.shuffle(choices)

    st.session_state.slider_question = question
    st.session_state.slider_choices = choices
    st.session_state.slider_correct_index = choices.index(question["correct_answer"])
    st.session_state.slider_round_started = time.monotonic()


def step_marker():
    if st.session_state.get("slider_over", True):
        return
    speed = 2 + st.session_state.slider_level * 2
    position = st.session_state.slider_position + st.session_state.slider_direction * speed
    if position >= 100:
        st.session_state.slider_position = 100
        st.session_state.slider_direction = -1
    elif position <= 0:
        st.session_state.slider_position = 0
        st.session_state.slider_direction = 1
    else:
        st.session_state.slider_position = position


def end_slider():
    if st.session_state.slider_wins >= MINIMUM_WINS:
        elapsed = nierva_timer.stop_timer("slider")
        message = (
            f"🎉 You cleared {st.session_state.slider_wins} of {TOTAL_SLIDERS} sliders "
            f"in {nierva_timer.format_time(elapsed)}!"
        )
        nierva_progression.finish_game("Slider", message)
        return

    st.session_state.slider_over = True
    elapsed = nierva_timer.stop_timer("slider")
    st.session_state.slider_msg = (
        f"❌ You cleared {st.session_state.slider_wins} of {TOTAL_SLIDERS} sliders. "
        f"You needed {MINIMUM_WINS} to continue. "
        f"Game over after {nierva_timer.format_time(elapsed)}."
    )
    nierva_progression.record_failure("Slider")


def finish_round(won, reason=""):
    level = st.session_state.slider_level
    question = st.session_state.slider_question
    choices = st.session_state.slider_choices
    position = st.session_state.slider_position
    st.session_state.slider_history.append({
        "level": level,
        "question": question["question"],
        "choices": choices,
        "position": position,
        "won": won,
    })

    if won:
        answer = choices[st.session_state.slider_correct_index]
        get_save_data().record_clear(
            "Slider Minigame",
            level,
            f"Answered {answer} at {position:.1f}%",
        )
        st.session_state.slider_wins += 1
        st.session_state.slider_msg = f"✅ Correct! Level {level} cleared."
    else:
        st.session_state.slider_msg = (
            f"⌛ Time expired on level {level}." if reason else
            f"❌ Incorrect choice. The answer was {question['correct_answer']}."
        )

    if level >= TOTAL_SLIDERS:
        end_slider()
        return

    st.session_state.slider_level += 1
    st.session_state.slider_position = 50
    st.session_state.slider_direction = 1
    set_slider_question()


def lock_slider():
    if st.session_state.slider_over:
        return
    if check_round_timeout():
        return
    selected_index = min(int(st.session_state.slider_position // 25), 3)
    finish_round(selected_index == st.session_state.slider_correct_index)


def check_round_timeout():
    if st.session_state.slider_over:
        return False
    limit = SLIDER_TIMES[st.session_state.slider_level - 1]
    elapsed = time.monotonic() - st.session_state.slider_round_started
    if elapsed < limit:
        return False
    finish_round(False, reason="timeout")
    return True


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


def render_active_slider():
    run_every = 0.1 if not st.session_state.slider_over else None

    @st.fragment(run_every=run_every)
    def draw():
        if check_round_timeout():
            st.rerun()
        step_marker()
        render_slider_bar(
            st.session_state.slider_choices,
            st.session_state.slider_position,
        )

    draw()


def main():
    st.write("# 🎚️ Slider Precision Minigame")
    st.caption("Answer each question by stopping the marker over the correct choice.")

    save_data = get_save_data()
    if "slider_level" not in st.session_state:
        init_slider()

    reset_col, score_col, timer_col, new_game_col = st.columns([1, 1, 1.2, 1])
    if new_game_col.button("New Game"):
        init_slider()
        st.rerun()
    reset_col.metric(
        "Level",
        f"{st.session_state.slider_level}/{TOTAL_SLIDERS}",
    )
    score_col.metric("Saved Score", save_data.check_score())
    with timer_col:
        nierva_timer.render_timer_display("slider", label="Game Time")

    for completed in st.session_state.slider_history:
        result = "cleared" if completed["won"] else "missed"
        st.caption(f"Level {completed['level']} {result}")
        st.caption(completed["question"])
        render_slider_bar(completed["choices"], completed["position"])

    if not st.session_state.slider_over:
        level = st.session_state.slider_level
        time_limit = SLIDER_TIMES[level - 1]
        st.caption(f"Current Level {level} | {time_limit} seconds")
        question = st.session_state.slider_question
        st.info(question["question"])
        st.caption(f"Subject: {question['game']} | Difficulty: {question['difficulty']}")
        render_active_slider()

        stop_col, tick_col = st.columns(2)
        stop_col.button(
            "🛑 STOP SLIDER (LMB)",
            on_click=lock_slider,
            width="stretch",
        )
        tick_col.button(
            "⏩ Tick Marker Movement",
            on_click=step_marker,
            width="stretch",
        )
        if st.session_state.slider_msg:
            st.success(st.session_state.slider_msg)
    else:
        st.error(st.session_state.slider_msg)
        st.button("New Game", on_click=init_slider)


if __name__ == "__main__":
    main()
