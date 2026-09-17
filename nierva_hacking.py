import streamlit as st
import random
import nierva_timer

WORD_LIST = [
    "SYSTEM", "ACCESS", "CIPHER", "HACKER", "SIGNAL", "MATRIX",
    "SERVER", "BINARY", "SAFETY", "ROUTER", "SHIELD", "OUTPUT"
]

def init_hacking():
    st.session_state.hack_password = random.choice(WORD_LIST)
    st.session_state.hack_words = random.sample(WORD_LIST, 6)
    if st.session_state.hack_password not in st.session_state.hack_words:
        st.session_state.hack_words[0] = st.session_state.hack_password
    random.shuffle(st.session_state.hack_words)
    st.session_state.hack_attempts = 8
    st.session_state.hack_log = []
    st.session_state.hack_over = False
    st.session_state.hack_win = False
    nierva_timer.start_timer("hacking")

def shuffle_words():
    random.shuffle(st.session_state.hack_words)

def evaluate_guess(guess: str) -> str:
    pwd = st.session_state.hack_password
    res = []
    for i, char in enumerate(guess):
        if char == pwd[i]:
            res.append(char)
        elif char in pwd:
            res.append("#")
        else:
            res.append("-")
    return "".join(res)

def pick_word(word: str):
    if st.session_state.hack_over:
        return
    st.session_state.hack_attempts -= 1
    feedback = evaluate_guess(word)
    st.session_state.hack_log.append((word, feedback))

    if word == st.session_state.hack_password:
        st.session_state.hack_win = True
        st.session_state.hack_over = True
        nierva_timer.stop_timer("hacking")
    elif st.session_state.hack_attempts <= 0:
        st.session_state.hack_over = True
        nierva_timer.stop_timer("hacking")

def main():
    st.write('# 🔐 Terminal Password Decryption Game')
    st.caption('Deduction mechanics prototype: Find the correct key sequence using positional feedback.')

    if 'hack_password' not in st.session_state:
        init_hacking()

    c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1])
    c1.metric('Attempts Left', f"{st.session_state.hack_attempts}/8")
    c2.metric('Status', 'UNLOCKED' if st.session_state.hack_win else ('LOCKED' if not st.session_state.hack_over else 'FAILED'))
    with c3:
        nierva_timer.render_timer_display("hacking", label="Decryption Time")
    if c4.button('Reset Terminal'):
        init_hacking()

    main_col, log_col = st.columns([1.2, 1])

    with main_col:
        st.markdown("#### 📡 Encrypted Keyword Stream:")
        for w in st.session_state.hack_words:
            st.button(
                f"❯ {w}",
                key=f"hack_w_{w}",
                on_click=pick_word,
                args=(w,),
                disabled=st.session_state.hack_over,
                use_container_width=True
            )
        st.button('🔄 Shuffle Stream Positions', on_click=shuffle_words)

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
