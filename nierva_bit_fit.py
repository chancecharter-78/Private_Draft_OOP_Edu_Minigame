import streamlit as st
import random
import string
import time
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
    answer_letters_by_column = [None] * column_count
    answer_index = 0
    for idx, active in enumerate(active_columns):
        correct_letter = answer[answer_index] if active else None
        if active:
            answer_letters_by_column[idx] = correct_letter
            answer_index += 1
        distractors = [letter for letter in string.ascii_uppercase if letter != correct_letter]
        choices = ([correct_letter] if correct_letter else []) + random.sample(distractors, 3 if not active else 2)
        random.shuffle(choices)
        options_by_column.append(choices)
        selected_by_column.append(next(
            (letter for letter in choices if letter != correct_letter), choices[0]
        ))

    active_indexes = [idx for idx, active in enumerate(active_columns) if active]
    early_reveal_count = min(random.randint(1, 2), len(active_indexes))
    early_schedules = []
    for _ in range(early_reveal_count):
        dash_start = random.uniform(6.0, 15.0)
        hash_start = dash_start + random.uniform(1.5, 2.5)
        letter_reveal = hash_start + random.uniform(1.5, 2.5)
        early_schedules.append((letter_reveal, dash_start, hash_start))
    early_schedules.sort()

    later_reveal_count = len(active_indexes) - early_reveal_count
    full_reveal_time = max(
        random.triangular(16.0, 25.0, 18.0),
        early_schedules[-1][0] + 1.5,
    )
    later_reveal_times = []
    if later_reveal_count > 1:
        earliest_later_reveal = early_schedules[-1][0] + 0.5
        later_reveal_times = sorted(
            random.uniform(earliest_later_reveal, full_reveal_time - 1.0)
            for _ in range(later_reveal_count - 1)
        )
    if later_reveal_count:
        later_reveal_times.append(full_reveal_time)

    reveal_schedules = list(early_schedules)
    for letter_reveal in later_reveal_times:
        dash_duration = random.uniform(1.5, 2.5)
        hash_duration = random.uniform(1.5, 2.5)
        dash_start = letter_reveal - dash_duration - hash_duration
        hash_start = dash_start + dash_duration
        reveal_schedules.append((letter_reveal, dash_start, hash_start))

    answer_reveal_stages = [None] * column_count
    reveal_order = random.sample(active_indexes, len(active_indexes))
    for idx, (letter_reveal, dash_start, hash_start) in zip(reveal_order, reveal_schedules):
        answer_reveal_stages[idx] = (dash_start, hash_start, letter_reveal)

    st.session_state.bf_question = question
    st.session_state.bf_answer = answer
    st.session_state.bf_cols = column_count
    st.session_state.bf_active = active_columns
    st.session_state.bf_options = options_by_column
    st.session_state.bf_player = selected_by_column
    st.session_state.bf_answer_letters = answer_letters_by_column
    st.session_state.bf_answer_reveal_stages = answer_reveal_stages
    st.session_state.bf_reveal_started = time.monotonic()


def init_bit_fit():
    st.session_state.bf_round = 1
    st.session_state.bf_over = False
    st.session_state.bf_msg = ""
    setup_round()
    nierva_timer.start_timer("bit_fit")

def cycle_letter(idx):
    if not st.session_state.bf_over and st.session_state.bf_active[idx]:
        choices = st.session_state.bf_options[idx]
        current_index = choices.index(st.session_state.bf_player[idx])
        st.session_state.bf_player[idx] = choices[(current_index + 1) % len(choices)]

def submit_round():
    save_data = get_save_data()
    active_indexes = [
        idx for idx, active in enumerate(st.session_state.bf_active) if active
    ]
    submitted_word = "".join(
        st.session_state.bf_player[idx] for idx in active_indexes
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


@st.fragment(run_every=0.25)
def render_cipher_columns():
    top_columns = st.columns(st.session_state.bf_cols)
    button_columns = st.columns(st.session_state.bf_cols)
    elapsed = time.monotonic() - st.session_state.bf_reveal_started

    for idx in range(st.session_state.bf_cols):
        if st.session_state.bf_active[idx]:
            dash_start, hash_start, letter_reveal = st.session_state.bf_answer_reveal_stages[idx]
            if elapsed < dash_start:
                displayed_text = " "
            elif elapsed < hash_start:
                displayed_text = "-"
            elif elapsed < letter_reveal:
                displayed_text = "#"
            else:
                displayed_text = st.session_state.bf_answer_letters[idx]
            top_columns[idx].markdown(
                f"<div style='text-align:center;font-size:1.35rem;font-weight:700'>"
                f"{displayed_text}</div>",
                unsafe_allow_html=True,
            )
        else:
            top_columns[idx].markdown(
                "<div style='text-align:center;color:#777'>-</div>",
                unsafe_allow_html=True,
            )
            top_columns[idx].caption("-")

        button_columns[idx].button(
            st.session_state.bf_player[idx],
            key=f"bf_cycle_{idx}",
            on_click=cycle_letter,
            args=(idx,),
            disabled=not st.session_state.bf_active[idx] or st.session_state.bf_over,
            use_container_width=True,
        )


def main():
    st.write('# 💻 Bit Fit Binary Matching Game')
    st.caption('Choose one of three letters in each active column to decode the answer.')

    save_data = get_save_data()

    if (
        'bf_round' not in st.session_state
        or 'bf_options' not in st.session_state
        or 'bf_answer_reveal_stages' not in st.session_state
    ):
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
    render_cipher_columns()

    st.markdown("---")
    st.markdown("### 🔀 Cycle the Letter in Each Active Column:")

    st.markdown("")
    if not st.session_state.bf_over:
        st.button('⚡ Decode Word', on_click=submit_round, use_container_width=True)
        if st.session_state.bf_msg:
            st.success(st.session_state.bf_msg)
    else:
        st.error(st.session_state.bf_msg)

if __name__ == '__main__':
    main()
