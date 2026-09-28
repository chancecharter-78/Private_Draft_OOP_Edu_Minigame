import streamlit as st
import random
from html import escape
import nierva_timer
import nierva_progression
from nierva_save_data import GameSaveData, ensure_current_save_data

MAX_SLIDER_BARS = 5

def get_save_data() -> GameSaveData:
    st.session_state.save_data = ensure_current_save_data(
        st.session_state.get("save_data", st.session_state.get("nierva_save_data"))
    )
    return st.session_state.save_data

def init_slider():
    st.session_state.slider_level = 1
    st.session_state.slider_history = []
    st.session_state.slider_position = 50
    st.session_state.slider_direction = 1
    st.session_state.slider_over = False
    st.session_state.slider_msg = ""
    set_slider_question()
    nierva_timer.start_timer("slider")

def set_slider_question():
    previous_question = None
    if "slider_question" in st.session_state:
        previous_question = st.session_state.slider_question["question"]
    question = get_save_data().get_random_question(previous_question)
    choices = [question["correct_answer"], *question["wrong_answers"]]
    random.shuffle(choices)
    st.session_state.slider_question = question
    st.session_state.slider_choices = choices
    st.session_state.slider_correct_index = choices.index(question["correct_answer"])

def step_marker():
    if st.session_state.slider_over:
        return
    speed = 2 + st.session_state.slider_level * 2
    st.session_state.slider_position += st.session_state.slider_direction * speed
    if st.session_state.slider_position >= 100:
        st.session_state.slider_position = 100
        st.session_state.slider_direction = -1
    elif st.session_state.slider_position <= 0:
        st.session_state.slider_position = 0
        st.session_state.slider_direction = 1

def lock_slider():
    save_data = get_save_data()
    pos = st.session_state.slider_position
    selected_index = min(int(pos // 25), 3)
    question = st.session_state.slider_question
    if selected_index == st.session_state.slider_correct_index:
        answer = st.session_state.slider_choices[selected_index]
        save_data.record_clear(
            "Slider Minigame",
            st.session_state.slider_level,
            f"Answered {answer} at {pos:.1f}%",
        )
        if nierva_progression.record_success("Slider"):
            return
        st.session_state.slider_history.append({
            'level': st.session_state.slider_level,
            'question': question["question"],
            'choices': st.session_state.slider_choices,
            'position': pos,
        })
        st.session_state.slider_history = st.session_state.slider_history[-(MAX_SLIDER_BARS - 1):]
        st.session_state.slider_level += 1
        st.session_state.slider_position = 50
        st.session_state.slider_direction = 1
        set_slider_question()
        st.session_state.slider_msg = f"✅ Correct! Level {st.session_state.slider_level - 1} cleared."
    else:
        st.session_state.slider_over = True
        elapsed = nierva_timer.stop_timer("slider")
        st.session_state.slider_msg = (
            f"❌ Incorrect choice. The answer was {question['correct_answer']}. "
            f"Game over after {nierva_timer.format_time(elapsed)}."
        )

def render_slider_bar(choices, pos):
    choice_boxes = "".join(
        "<div style='display:flex;align-items:center;justify-content:center;"
        "position:relative;z-index:2;min-width:0;min-height:72px;padding:6px;border:2px solid #697586;"
        "border-radius:4px;background:#202a36;color:#fff;text-align:center;"
        "overflow-wrap:anywhere;font-weight:600;'>"
        f"{escape(choice)}</div>"
        for choice in choices
    )
    track_html = f"""
    <div style="position:relative;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px;width:100%;margin:15px 0 28px;">
        {choice_boxes}
        <div style="position:absolute;z-index:1;left:{pos}%;top:-9px;width:5px;height:88px;background:#f6c453;border:1px solid #202020;transform:translateX(-50%);"></div>
    </div>
    """
    st.markdown(track_html, unsafe_allow_html=True)

def main():
    st.write('# 🎚️ Slider Precision Minigame')
    st.caption('Answer each question by stopping the marker over the correct choice.')

    save_data = get_save_data()

    if 'slider_level' not in st.session_state or 'slider_history' not in st.session_state:
        init_slider()

    c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1])
    c1.metric('Level', st.session_state.slider_level)
    c2.metric('Saved Score', save_data.check_score())
    with c3:
        nierva_timer.render_timer_display("slider", label="Game Time")
    if c4.button('New Game'):
        init_slider()

    for completed_bar in st.session_state.slider_history:
        st.caption(f"Completed Level {completed_bar['level']}")
        st.caption(completed_bar["question"])
        render_slider_bar(completed_bar["choices"], completed_bar["position"])

    st.caption(f"Current Level {st.session_state.slider_level}")
    question = st.session_state.slider_question
    st.info(question["question"])
    st.caption(f"Difficulty: {question['difficulty']}")
    render_slider_bar(st.session_state.slider_choices, st.session_state.slider_position)

    b1, b2 = st.columns(2)
    if not st.session_state.slider_over:
        b1.button('🛑 STOP SLIDER (LMB)', on_click=lock_slider, use_container_width=True)
        b2.button('⏩ Tick Marker Movement', on_click=step_marker, use_container_width=True)
    else:
        st.error(st.session_state.slider_msg)

    if st.session_state.slider_msg and not st.session_state.slider_over:
        st.success(st.session_state.slider_msg)

if __name__ == '__main__':
    main()
