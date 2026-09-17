import streamlit as st
import random
import nierva_timer

def random_active_columns(column_count, round_number):
    minimum_active = min(column_count, max(3, round_number + 1))
    maximum_active = min(column_count, max(minimum_active, 2 * round_number + 1))
    active_count = random.randint(minimum_active, maximum_active)
    active_indexes = random.sample(range(column_count), active_count)
    active_columns = [False] * column_count
    for idx in active_indexes:
        active_columns[idx] = True
    return active_columns

def init_bit_fit():
    st.session_state.bf_round = 1
    st.session_state.bf_cols = 8
    st.session_state.bf_falling = [random.choice([0, 1]) for _ in range(st.session_state.bf_cols)]
    st.session_state.bf_player = [random.choice([0, 1]) for _ in range(st.session_state.bf_cols)]
    st.session_state.bf_active = random_active_columns(st.session_state.bf_cols, st.session_state.bf_round)
    st.session_state.bf_over = False
    st.session_state.bf_score = 0
    st.session_state.bf_msg = ""
    nierva_timer.start_timer("bit_fit")

def toggle_bit(idx):
    if not st.session_state.bf_over and st.session_state.bf_active[idx]:
        st.session_state.bf_player[idx] = 1 - st.session_state.bf_player[idx]

def submit_round():
    matches_active_columns = all(
        not active or st.session_state.bf_player[idx] == st.session_state.bf_falling[idx]
        for idx, active in enumerate(st.session_state.bf_active)
    )
    if matches_active_columns:
        st.session_state.bf_score += 10 * st.session_state.bf_round
        st.session_state.bf_round += 1
        st.session_state.bf_falling = [random.choice([0, 1]) for _ in range(st.session_state.bf_cols)]
        st.session_state.bf_player = [random.choice([0, 1]) for _ in range(st.session_state.bf_cols)]
        st.session_state.bf_active = random_active_columns(st.session_state.bf_cols, st.session_state.bf_round)
        st.session_state.bf_msg = f"🎉 Match complete! Round {st.session_state.bf_round} started."
    else:
        st.session_state.bf_over = True
        elapsed = nierva_timer.stop_timer("bit_fit")
        st.session_state.bf_msg = f"❌ Bit mismatch! Bit Fit sequence failed in {nierva_timer.format_time(elapsed)}."

def main():
    st.write('# 💻 Bit Fit Binary Matching Game')
    st.caption('Binary mechanics prototype: Match the bottom bit array to the target pattern above.')

    if 'bf_round' not in st.session_state or 'bf_active' not in st.session_state:
        init_bit_fit()

    c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1])
    c1.metric('Round', st.session_state.bf_round)
    c2.metric('Score', st.session_state.bf_score)
    with c3:
        nierva_timer.render_timer_display("bit_fit", label="Session Time")
    if c4.button('Restart Bit Fit'):
        init_bit_fit()

    st.markdown("### ⬇️ Target Bit Stream:")
    cols_top = st.columns(st.session_state.bf_cols)
    for idx, bit in enumerate(st.session_state.bf_falling):
        color = '#00ff00' if st.session_state.bf_active[idx] else '#777777'
        cols_top[idx].markdown(f"<h2 style='text-align: center; color: {color};'>{bit}</h2>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔀 Player Register Bits (Click to Toggle):")
    cols_bot = st.columns(st.session_state.bf_cols)
    for idx in range(st.session_state.bf_cols):
        p_bit = st.session_state.bf_player[idx]
        cols_bot[idx].button(
            str(p_bit),
            key=f"bit_toggle_{idx}",
            on_click=toggle_bit,
            args=(idx,),
            disabled=not st.session_state.bf_active[idx] or st.session_state.bf_over,
            use_container_width=True
        )

    st.markdown("")
    if not st.session_state.bf_over:
        st.button('⚡ Lock & Submit Register', on_click=submit_round, use_container_width=True)
        if st.session_state.bf_msg:
            st.success(st.session_state.bf_msg)
    else:
        st.error(st.session_state.bf_msg)

if __name__ == '__main__':
    main()
