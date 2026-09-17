import streamlit as st
import random
import nierva_timer
from nierva_save_data import GameSaveData

WORD_LIST = [
    "SYSTEM", "ACCESS", "CIPHER", "HACKER", "SIGNAL", "MATRIX",
    "SERVER", "BINARY", "SAFETY", "ROUTER", "SHIELD", "OUTPUT"
]
TERMINAL_DUMP_LINES = 20
TERMINAL_DUMP_WIDTH = 41
NOISE_CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$#@%&!?+-*/"

def get_save_data() -> GameSaveData:
    if "save_data" not in st.session_state:
        st.session_state.save_data = GameSaveData()
    return st.session_state.save_data

def generate_terminal_dump(words):
    dump = [
        [random.choice(NOISE_CHARACTERS) for _ in range(TERMINAL_DUMP_WIDTH)]
        for _ in range(TERMINAL_DUMP_LINES)
    ]
    placements = []
    for word in words:
        for _ in range(100):
            row = random.randrange(TERMINAL_DUMP_LINES)
            start = random.randrange(TERMINAL_DUMP_WIDTH - len(word) + 1)
            end = start + len(word)
            if all(
                placed_row != row or end <= placed_start or start >= placed_end
                for placed_row, placed_start, placed_end in placements
            ):
                dump[row][start:end] = word
                placements.append((row, start, end))
                break
    return "\n".join("".join(row) for row in dump)

def init_hacking():
    st.session_state.hack_password = random.choice(WORD_LIST)
    st.session_state.hack_words = random.sample(WORD_LIST, 6)
    if st.session_state.hack_password not in st.session_state.hack_words:
        st.session_state.hack_words[0] = st.session_state.hack_password
    random.shuffle(st.session_state.hack_words)
    st.session_state.hack_terminal_dump = generate_terminal_dump(st.session_state.hack_words)
    st.session_state.hack_attempts = 8
    st.session_state.hack_log = []
    st.session_state.hack_input = ""
    st.session_state.hack_over = False
    st.session_state.hack_win = False
    nierva_timer.start_timer("hacking")

def shuffle_words():
    random.shuffle(st.session_state.hack_words)

def evaluate_guess(guess: str) -> str:
    pwd = st.session_state.hack_password
    res = []
    for i, char in enumerate(guess):
        if i < len(pwd) and char == pwd[i]:
            res.append(char)
        elif char in pwd:
            res.append("#")
        else:
            res.append("-")
    return "".join(res)

def pick_word(word: str):
    save_data = get_save_data()
    if st.session_state.hack_over:
        return
    word = word.strip().upper()
    if not word:
        return
    st.session_state.hack_attempts -= 1
    feedback = evaluate_guess(word)
    st.session_state.hack_log.append((word, feedback))

    if word == st.session_state.hack_password:
        st.session_state.hack_win = True
        st.session_state.hack_over = True
        elapsed = nierva_timer.stop_timer("hacking")
        save_data.record_clear("Terminal Hacking", 1, f"Password Decrypted in {nierva_timer.format_time(elapsed)}")
    elif st.session_state.hack_attempts <= 0:
        st.session_state.hack_over = True
        nierva_timer.stop_timer("hacking")

def main():
    st.write('# 🔐 Terminal Password Decryption Game')
    st.caption('Deduction mechanics prototype: Find the correct key sequence using positional feedback.')

    save_data = get_save_data()

    if (
        'hack_password' not in st.session_state
        or 'hack_terminal_dump' not in st.session_state
        or 'hack_input' not in st.session_state
    ):
        init_hacking()

    c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1])
    c1.metric('Attempts Left', f"{st.session_state.hack_attempts}/8")
    c2.metric('Saved Score', save_data.check_score())
    with c3:
        nierva_timer.render_timer_display("hacking", label="Decryption Time")
    if c4.button('Reset Terminal'):
        init_hacking()

    main_col, log_col = st.columns([1.2, 1])

    with main_col:
        st.markdown("#### ▒ Encrypted Terminal Dump:")
        st.code(st.session_state.hack_terminal_dump, language="text")
        st.markdown("#### 🔑 Enter Password:")
        st.text_input(
            "Password",
            key="hack_input",
            max_chars=12,
            disabled=st.session_state.hack_over,
            label_visibility="collapsed",
        )
        st.button(
            "Submit Password",
            on_click=pick_word,
            args=(st.session_state.hack_input,),
            disabled=st.session_state.hack_over,
            use_container_width=True,
        )

    with log_col:
        st.markdown("#### 📋 Diagnostic Log:")
        st.info(
            "**Legend**:\n"
            "- `Letter`: Exact match (correct position)\n"
            "- `#`: Character exists (wrong position)\n"
            "- `-`: Character absent"
        )
        for w, fb in reversed(st.session_state.hack_log):
            st.code(f"> {w} -> FEEDBACK: {fb}")

    if st.session_state.hack_win:
        elapsed = nierva_timer.get_elapsed("hacking")
        st.success(f"🎉 Decryption Complete in {nierva_timer.format_time(elapsed)}! Target sequence was **{st.session_state.hack_password}**.")
    elif st.session_state.hack_over:
        st.error(f"💀 Lockout Triggered! Sequence was **{st.session_state.hack_password}**.")

if __name__ == '__main__':
    main()
