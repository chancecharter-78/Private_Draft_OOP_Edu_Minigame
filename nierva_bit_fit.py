import streamlit as st
import random
import string
import nierva_timer
import nierva_progression
from nierva_save_data import GameSaveData, ensure_current_save_data

def get_save_data() -> GameSaveData:
    st.session_state.save_data = ensure_current_save_data(
        st.session_state.get("save_data", st.session_state.get("nierva_save_data"))
    )
    return st.session_state.save_data

def random_active_columns(column_count, word_length):
    active_indexes = random.sample(range(column_count), min(column_count, word_length))
    active_columns = [False] * column_count
    for idx in active_indexes:
        active_columns[idx] = True
    return active_columns

def setup_round():
    previous_question = st.session_state.get("bf_question", {}).get("question")
    question = get_save_data().get_random_question(previous_question)
    answer = question["correct_answer"]
    column_count = max(10, len(answer))
    active_columns = random_active_columns(column_count, len(answer))

    options_by_column = []
    selected_by_column = []
    answer_index = 0
    for idx, active in enumerate(active_columns):
        correct_letter = answer[answer_index] if active else None
        if active:
            answer_index += 1
        distractors = [letter for letter in string.ascii_uppercase if letter != correct_letter]
        choices = ([correct_letter] if correct_letter else []) + random.sample(distractors, 3 if not active else 2)
        random.shuffle(choices)
        options_by_column.append(choices)
        selected_by_column.append(next(
            (letter for letter in choices if letter != correct_letter), choices[0]
        ))

    st.session_state.bf_question = question
    st.session_state.bf_answer = answer
    st.session_state.bf_cols = column_count
    st.session_state.bf_active = active_columns
    st.session_state.bf_options = options_by_column
    st.session_state.bf_player = selected_by_column
    for idx, selected_letter in enumerate(selected_by_column):
        st.session_state[f"bf_choice_{idx}"] = selected_letter


def init_bit_fit():
    st.session_state.bf_round = 1
    st.session_state.bf_over = False
    st.session_state.bf_msg = ""
    setup_round()
    nierva_timer.start_timer("bit_fit")

def toggle_bit(idx):
    if not st.session_state.bf_over and st.session_state.bf_active[idx]:
        st.session_state.bf_player[idx] = 1 - st.session_state.bf_player[idx]

def submit_round():
    save_data = get_save_data()
    active_indexes = [
        idx for idx, active in enumerate(st.session_state.bf_active) if active
    ]
    submitted_word = "".join(
        st.session_state.get(f"bf_choice_{idx}", st.session_state.bf_player[idx])
        for idx in active_indexes
    )
    if submitted_word == st.session_state.bf_answer:
        save_data.record_clear("Bit Fit", st.session_state.bf_round, f"Decoded {submitted_word}")
        if nierva_progression.record_success("Bit Fit"):
            return
        st.session_state.bf_round += 1
        setup_round()
        st.session_state.bf_msg = f"🎉 Correct! Round {st.session_state.bf_round} started."
    else:
        st.session_state.bf_over = True
        elapsed = nierva_timer.stop_timer("bit_fit")
        st.session_state.bf_msg = (
            f"❌ The letters decoded to {submitted_word or '(empty)'}, not "
            f"{st.session_state.bf_answer}. Failed in {nierva_timer.format_time(elapsed)}."
        )

def main():
    st.write('# 🔤 Bit Fit Letter Cipher')
    st.caption('Choose one of three letters in each active column to decode the answer.')

    save_data = get_save_data()

    if 'bf_round' not in st.session_state or 'bf_options' not in st.session_state:
        init_bit_fit()

    c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1])
    c1.metric('Round', st.session_state.bf_round)
    c2.metric('Saved Score', save_data.check_score())
    with c3:
        nierva_timer.render_timer_display("bit_fit", label="Session Time")
    if c4.button('Restart Bit Fit'):
        init_bit_fit()

    question = st.session_state.bf_question
    st.info(question["question"])
    st.caption(f"Difficulty: {question['difficulty']} | Active columns read left to right.")

    st.markdown("### 🔎 Letter Cipher Columns:")
    cols_top = st.columns(st.session_state.bf_cols)
    for idx, choices in enumerate(st.session_state.bf_options):
        if st.session_state.bf_active[idx]:
            display_choices = "<br>".join(choices)
            cols_top[idx].markdown(
                f"<div style='text-align:center;color:#17834b;font-weight:700'>{display_choices}</div>",
                unsafe_allow_html=True,
            )
            cols_top[idx].caption(f"{idx + 1}")
        else:
            cols_top[idx].markdown("<div style='text-align:center;color:#777'>-</div>", unsafe_allow_html=True)
            cols_top[idx].caption("-")

    st.markdown("---")
    st.markdown("### 🔀 Select a Letter in Each Active Column:")
    cols_bot = st.columns(st.session_state.bf_cols)
    for idx in range(st.session_state.bf_cols):
        selected = cols_bot[idx].selectbox(
            f"Column {idx + 1}",
            options=st.session_state.bf_options[idx],
            key=f"bf_choice_{idx}",
            disabled=not st.session_state.bf_active[idx] or st.session_state.bf_over,
            label_visibility="collapsed",
        )
        st.session_state.bf_player[idx] = selected

    st.markdown("")
    if not st.session_state.bf_over:
        st.button('⚡ Decode Word', on_click=submit_round, use_container_width=True)
        if st.session_state.bf_msg:
            st.success(st.session_state.bf_msg)
    else:
        st.error(st.session_state.bf_msg)

if __name__ == '__main__':
    main()
