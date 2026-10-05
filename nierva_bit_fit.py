import random
import string
import time

import streamlit as st

import nierva_progression
import nierva_timer
from nierva_save_data import ensure_current_save_data


def get_save_data():
    st.session_state.save_data = ensure_current_save_data(
        st.session_state.get("save_data")
    )
    return st.session_state.save_data


def random_active_columns(column_count, answer_length):
    active_indexes = random.sample(range(column_count), answer_length)
    return [index in active_indexes for index in range(column_count)]


def make_reveal_schedules(letter_count):
    early_count = min(random.randint(1, 2), max(0, letter_count - 1))
    early_schedules = []

    for _ in range(early_count):
        dash_start = random.uniform(6, 15)
        hash_start = dash_start + random.uniform(1.5, 2.5)
        letter_time = hash_start + random.uniform(1.5, 2.5)
        early_schedules.append((dash_start, hash_start, letter_time))

    final_reveal = max(
        random.triangular(16, 25, 18),
        max((item[2] for item in early_schedules), default=0) + 1.5,
    )
    later_count = letter_count - early_count
    later_times = []
    if later_count > 1:
        earliest = max((item[2] for item in early_schedules), default=0) + 0.5
        later_times = sorted(
            random.uniform(earliest, final_reveal - 1)
            for _ in range(later_count - 1)
        )
    if later_count:
        later_times.append(final_reveal)

    schedules = list(early_schedules)
    for letter_time in later_times:
        hash_start = letter_time - random.uniform(1.5, 2.5)
        dash_start = hash_start - random.uniform(1.5, 2.5)
        schedules.append((dash_start, hash_start, letter_time))
    return schedules


def setup_round():
    previous_question = st.session_state.get("bf_question", {}).get("question")
    question = get_save_data().get_random_question(previous_question)
    answer = question["correct_answer"]
    column_count = max(10, len(answer))
    active_columns = random_active_columns(column_count, len(answer))
    option_count = min(3 + st.session_state.bf_round - 1, 10)

    options = []
    player_letters = []
    answer_letters = [None] * column_count
    active_indexes = [index for index, active in enumerate(active_columns) if active]

    for index, active in enumerate(active_columns):
        correct_letter = answer[active_indexes.index(index)] if active else None
        if active:
            answer_letters[index] = correct_letter
            other_letters = [letter for letter in string.ascii_uppercase if letter != correct_letter]
            choices = [correct_letter] + random.sample(other_letters, option_count - 1)
        else:
            choices = random.sample(list(string.ascii_uppercase), option_count)
        random.shuffle(choices)
        options.append(choices)
        player_letters.append(random.choice([letter for letter in choices if letter != correct_letter]))

    schedules = make_reveal_schedules(len(answer))
    random.shuffle(active_indexes)
    reveal_stages = [None] * column_count
    for index, schedule in zip(active_indexes, schedules):
        reveal_stages[index] = schedule

    st.session_state.bf_question = question
    st.session_state.bf_answer = answer
    st.session_state.bf_cols = column_count
    st.session_state.bf_active = active_columns
    st.session_state.bf_options = options
    st.session_state.bf_player = player_letters
    st.session_state.bf_answer_letters = answer_letters
    st.session_state.bf_answer_reveal_stages = reveal_stages
    st.session_state.bf_reveal_started = time.monotonic()
    st.session_state.bf_msg = ""


def init_bit_fit():
    st.session_state.bf_round = 1
    st.session_state.bf_over = False
    setup_round()
    nierva_timer.start_timer("bit_fit")


def cycle_letter(index):
    if st.session_state.bf_over or not st.session_state.bf_active[index]:
        return
    choices = st.session_state.bf_options[index]
    current = choices.index(st.session_state.bf_player[index])
    st.session_state.bf_player[index] = choices[(current + 1) % len(choices)]


def get_revealed_count(elapsed):
    return sum(
        1
        for stage in st.session_state.bf_answer_reveal_stages
        if stage is not None and elapsed >= stage[2]
    )


def calculate_points(round_number, revealed_count, letter_count):
    if revealed_count == 0:
        return 300 * round_number
    if revealed_count == letter_count:
        return 50 * round_number
    if revealed_count <= 3:
        return 250 * round_number
    return 100 * round_number


def lose_round(message):
    st.session_state.bf_over = True
    st.session_state.bf_msg = message
    nierva_timer.stop_timer("bit_fit")
    nierva_progression.record_failure("Bit Fit")


def submit_round():
    if st.session_state.bf_over:
        return

    active_indexes = [
        index for index, active in enumerate(st.session_state.bf_active) if active
    ]
    answer = "".join(st.session_state.bf_player[index] for index in active_indexes)
    if answer != st.session_state.bf_answer:
        elapsed = nierva_timer.stop_timer("bit_fit")
        lose_round(
            f"❌ The letters decoded to {answer or '(empty)'}, not "
            f"{st.session_state.bf_answer}. Failed in {nierva_timer.format_time(elapsed)}."
        )
        return

    revealed_count = get_revealed_count(
        time.monotonic() - st.session_state.bf_reveal_started
    )
    points = calculate_points(
        st.session_state.bf_round,
        revealed_count,
        len(active_indexes),
    )

    save_data = get_save_data()
    save_data.record_clear(
        "Bit Fit",
        st.session_state.bf_round,
        f"Decoded {answer} with {revealed_count} revealed letter(s)",
        points=points,
    )

    success_message = f"🎉 Correct! Round {st.session_state.bf_round} cleared."
    if nierva_progression.record_success("Bit Fit", success_message):
        return

    st.session_state.bf_round += 1
    setup_round()
    st.session_state.bf_msg = f"🎉 Correct! Round {st.session_state.bf_round} started."


def draw_cipher_columns():
    elapsed = time.monotonic() - st.session_state.bf_reveal_started
    for start in range(0, st.session_state.bf_cols, 5):
        indexes = range(start, min(start + 5, st.session_state.bf_cols))
        columns = st.columns(len(indexes))
        for column, index in zip(columns, indexes):
            active = st.session_state.bf_active[index]
            if not active:
                column.markdown("### -")
            else:
                dash_start, hash_start, reveal_time = (
                    st.session_state.bf_answer_reveal_stages[index]
                )
                if elapsed < dash_start:
                    displayed_text = " "
                elif elapsed < hash_start:
                    displayed_text = "-"
                elif elapsed < reveal_time:
                    displayed_text = "#"
                else:
                    displayed_text = st.session_state.bf_answer_letters[index]
                column.markdown(f"### {displayed_text}")

            column.button(
                st.session_state.bf_player[index],
                key=f"bf_cycle_{index}",
                on_click=cycle_letter,
                args=(index,),
                disabled=not active or st.session_state.bf_over,
                width="stretch",
            )


def render_cipher_columns():
    run_every = 0.1 if not st.session_state.bf_over else None

    @st.fragment(run_every=run_every)
    def draw():
        draw_cipher_columns()

    draw()


def main():
    st.write("# 💻 Bit Fit Binary Matching Game")
    st.caption("Choose a letter in each active column to decode the answer.")

    save_data = get_save_data()
    if "bf_round" not in st.session_state or "bf_options" not in st.session_state:
        init_bit_fit()

    reset_col, score_col, timer_col, restart_col = st.columns([1, 1, 1.2, 1])
    if restart_col.button("Restart Bit Fit"):
        nierva_progression.reset_game("Bit Fit")
        init_bit_fit()
        st.rerun()
    reset_col.metric("Round", st.session_state.bf_round)
    score_col.metric("Saved Score", save_data.check_score())
    with timer_col:
        nierva_timer.render_timer_display("bit_fit", label="Session Time")

    question = st.session_state.bf_question
    st.info(question["question"])
    st.caption(
        f"Subject: {question['game']} | Difficulty: {question['difficulty']} | "
        f"{len(st.session_state.bf_options[0])} choices per column. Active columns read left to right."
    )

    st.markdown("### 🔎 Letter Cipher Columns:")
    render_cipher_columns()
    st.markdown("---")
    st.markdown("### 🔀 Cycle the Letter in Each Active Column:")

    if not st.session_state.bf_over:
        st.button("⚡ Decode Word", on_click=submit_round, width="stretch")
        if st.session_state.bf_msg:
            st.success(st.session_state.bf_msg)
    else:
        st.error(st.session_state.bf_msg)


if __name__ == "__main__":
    main()
