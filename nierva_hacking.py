import random
import time

import streamlit as st

import nierva_progression
import nierva_timer
from nierva_save_data import ensure_current_save_data


TERMINAL_DUMP_LINES = 20
TERMINAL_DUMP_WIDTH = 41
NOISE_CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$#@%&!?+-*/"
ROUND_SECONDS = 30


def get_save_data():
    st.session_state.save_data = ensure_current_save_data(
        st.session_state.get("save_data")
    )
    return st.session_state.save_data


def generate_terminal_dump(words):
    width = max(TERMINAL_DUMP_WIDTH, *(len(word) for word in words))
    lines = [
        [random.choice(NOISE_CHARACTERS) for _ in range(width)]
        for _ in range(max(TERMINAL_DUMP_LINES, len(words)))
    ]
    rows = random.sample(range(len(lines)), len(words))

    for row, word in zip(rows, words):
        start = random.randint(0, width - len(word))
        lines[row][start:start + len(word)] = word
    return "\n".join("".join(line) for line in lines)


def init_hacking():
    previous_questions = st.session_state.get("hack_seen_questions", [])
    question = get_save_data().get_random_question(previous_questions)
    previous_questions.append(question["question"])
    st.session_state.hack_seen_questions = previous_questions
    words = [question["correct_answer"], *question["wrong_answers"]]
    random.shuffle(words)

    st.session_state.hack_question = question
    st.session_state.hack_password = question["correct_answer"]
    st.session_state.hack_words = words
    st.session_state.hack_terminal_dump = generate_terminal_dump(words)
    st.session_state.hack_attempts = len(words) - 1
    st.session_state.hack_log = []
    st.session_state.hack_input = ""
    st.session_state.hack_over = False
    st.session_state.hack_win = False
    st.session_state.hack_started = time.monotonic()
    nierva_timer.start_timer("hacking")


def evaluate_guess(guess, password):
    feedback = ["-"] * len(guess)
    remaining = {}

    for letter in password:
        remaining[letter] = remaining.get(letter, 0) + 1

    for index, letter in enumerate(guess):
        if index < len(password) and letter == password[index]:
            feedback[index] = letter
            remaining[letter] -= 1

    for index, letter in enumerate(guess):
        if feedback[index] == "-" and remaining.get(letter, 0) > 0:
            feedback[index] = "#"
            remaining[letter] -= 1

    return "".join(feedback)


def lose_round(message):
    st.session_state.hack_over = True
    st.session_state.hack_win = False
    st.session_state.hack_notice = message
    nierva_timer.stop_timer("hacking")
    nierva_progression.record_failure("Hacking")


def restart_hacking():
    seen_questions = st.session_state.get("hack_seen_questions", [])
    nierva_progression.reset_game("Hacking")
    st.session_state.hack_seen_questions = seen_questions


def check_timeout():
    if st.session_state.hack_over:
        return False
    if time.monotonic() - st.session_state.hack_started < ROUND_SECONDS:
        return False
    lose_round(f"⌛ Time's up! The sequence was {st.session_state.hack_password}.")
    return True


def pick_word():
    if st.session_state.hack_over:
        return
    if check_timeout():
        return

    guess = st.session_state.get("hack_input", "").strip().upper()
    st.session_state.hack_input = ""
    if not guess:
        st.session_state.hack_notice = "Enter a word from the terminal dump."
        return
    if guess not in st.session_state.hack_words:
        st.session_state.hack_notice = "Choose one of the words hidden in the terminal dump."
        return
    if any(previous_guess == guess for previous_guess, _ in st.session_state.hack_log):
        st.session_state.hack_notice = "You have already tried that word."
        return

    st.session_state.hack_attempts -= 1
    st.session_state.hack_log.append(
        (guess, evaluate_guess(guess, st.session_state.hack_password))
    )
    st.session_state.hack_notice = ""

    if guess == st.session_state.hack_password:
        st.session_state.hack_win = True
        st.session_state.hack_over = True
        elapsed = nierva_timer.stop_timer("hacking")
        message = (
            f"🎉 Decryption Complete in {nierva_timer.format_time(elapsed)}! "
            f"Target sequence was {st.session_state.hack_password}."
        )
        get_save_data().record_clear(
            "Terminal Hacking",
            1,
            f"Password decrypted in {nierva_timer.format_time(elapsed)}",
        )
        if nierva_progression.record_success("Hacking", message):
            return

        init_hacking()
        st.session_state.hack_notice = message
    elif st.session_state.hack_attempts <= 0:
        lose_round(f"💀 Lockout Triggered! Sequence was {st.session_state.hack_password}.")


def render_countdown():
    run_every = 0.1 if not st.session_state.hack_over else None

    @st.fragment(run_every=run_every)
    def draw():
        if check_timeout():
            st.rerun(scope="app")
        remaining = max(
            0,
            ROUND_SECONDS - (time.monotonic() - st.session_state.hack_started),
        )
        st.metric("Time Left", f"{remaining:04.1f}s")

    draw()


def main():
    st.write("# 🔐 Terminal Password Decryption Game")
    st.caption("Find the answer to the question hidden among the terminal noise.")

    save_data = get_save_data()
    if "hack_password" not in st.session_state or "hack_started" not in st.session_state:
        init_hacking()

    attempts_col, score_col, time_col, reset_col = st.columns([1, 1, 1.2, 1])
    reset_col.button(
        "Reset Terminal",
        on_click=restart_hacking,
        disabled=not st.session_state.hack_over,
    )
    attempts_col.metric(
        "Attempts Left",
        f"{st.session_state.hack_attempts}/{len(st.session_state.hack_words) - 1}",
    )
    score_col.metric("Saved Score", save_data.check_score())
    with time_col:
        render_countdown()

    main_col, log_col = st.columns([1.2, 1])
    with main_col:
        st.markdown("#### ▒ Encrypted Terminal Dump:")
        st.code(st.session_state.hack_terminal_dump, language="text")
        st.markdown("#### 🔑 Enter Password:")
        with st.form("hacking_guess"):
            st.text_input(
                "Password",
                key="hack_input",
                disabled=st.session_state.hack_over,
                label_visibility="collapsed",
            )
            st.form_submit_button(
                "Submit Password",
                on_click=pick_word,
                disabled=st.session_state.hack_over,
                width="stretch",
            )

    with log_col:
        st.markdown("#### 📋 Diagnostic Log:")
        question = st.session_state.hack_question
        st.text_area(
            "Question",
            value=question["question"],
            height=90,
            disabled=True,
        )
        st.caption(f"Subject: {question['game']} | Difficulty: {question['difficulty']}")
        st.info(
            "**Legend**:\n"
            "- `Letter`: Exact match (correct position)\n"
            "- `#`: Character exists (wrong position)\n"
            "- `-`: Character absent"
        )
        for word, feedback in reversed(st.session_state.hack_log):
            st.code(f"> {word} -> FEEDBACK: {feedback}")

    if st.session_state.get("hack_notice"):
        if st.session_state.hack_win:
            st.success(st.session_state.hack_notice)
        elif st.session_state.hack_over:
            st.error(st.session_state.hack_notice)
        else:
            st.info(st.session_state.hack_notice)
if __name__ == "__main__":
    main()
