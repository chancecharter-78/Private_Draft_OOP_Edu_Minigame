
from html import escape

import streamlit as st

from Controller import minigame as controller
from Controller.player import get_save_data
from Model import (
    bit_fit,
    game_flow,
    hacking,
    slider,
    timer,
)



TIMER_TICK_SECONDS = 0.2
START_GATE_REFRESH_SECONDS = 0.2


def _timer_metric(game_key, label):
    st.metric(
        label=label,
        value=timer.format_time(controller.get_elapsed(game_key)),
    )


@st.fragment(run_every=TIMER_TICK_SECONDS)
def _live_timer(game_key, label):
    _timer_metric(game_key, label)


def render_timer_display(game_key="default", label="Time Elapsed"):
    if controller.is_timer_active(game_key):
        _live_timer(game_key, label)
    else:
        _timer_metric(game_key, label)


def render_combo_status(label="Combo", visible=True):
    combo = controller.ensure_combo_state()
    if visible:
        st.caption(f"{label}: {combo['multiplier']:.2f}x · streak {combo['streak']}")
    return combo


@st.fragment(run_every=START_GATE_REFRESH_SECONDS)
def render_start_gate(game_name, timer_key):
    phase, countdown, announce_repair = controller.advance_start_gate(timer_key)
    if announce_repair:
        st.toast("Repair Sequence Starting", icon="🔧")
    if phase == "active":
        return True
    if phase == "delay":
        st.info("Get ready…")
        return False
    if phase == "countdown":
        st.markdown(f"## {countdown}")
        return False

    st.rerun()
    return True


def render_game_result(game_name, save_data):
    st.subheader("Repair Result")
    message = st.session_state.get("game_result_message", "")
    if message:
        st.info(message)

    if st.session_state.get("review_history", []):
        st.dataframe(
            controller.build_result_rows(),
            hide_index=True,
            width="stretch",
            column_config={
                column: (
                    st.column_config.NumberColumn(column, width=width)
                    if column == "Time (s)"
                    else st.column_config.TextColumn(column, width=width)
                )
                for column, width in game_flow.RESULT_COLUMN_WIDTHS.items()
            },
        )

        st.selectbox(
            "Rate your performance for this game",
            options=tuple(game_flow.RATING_LABELS),
            format_func=lambda rating: game_flow.RATING_LABELS[rating],
            key="review_user_rating",
        )
        st.button(
            "Continue",
            key=f"{game_name}_save_rating",
            on_click=controller.save_rating_and_continue,
            args=(game_name, save_data),
        )
        return

    st.button(
        "Continue",
        key=f"{game_name}_continue",
        on_click=controller.continue_to_next_game,
        args=(game_name,),
    )



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


@st.fragment(run_every=slider.SLIDER_REFRESH_SECONDS)
def render_active_slider():
    controller.update_marker()
    st.metric(
        "Game Time",
        timer.format_time(controller.get_elapsed("slider")),
    )
    render_combo_status("Combo", visible=False)
    render_slider_bar(
        st.session_state.slider_choices,
        st.session_state.slider_position,
    )


def render_slider_game_over():
    render_game_result("Slider", get_save_data())


def render_slider_page():
    st.write("# 🎚️ Slider Minigame")
    st.caption("Stop the marker over the correct answer.")

    save_data = get_save_data()
    controller.ensure_slider_ready()

    if st.session_state.get("game_result_ready", False):
        render_slider_game_over()
        return
    if not render_start_gate("Slider", "slider"):
        return
    controller.consume_slider_pending_start()

    level_col, score_col, new_game_col = st.columns([1, 1, 1])
    level_col.metric(
        "Level",
        f"{st.session_state.slider_level}/{slider.TOTAL_SLIDERS}",
    )
    score_col.metric("Saved Score", save_data.check_score())
    new_game_col.button(
        "New Game",
        key="slider_new_game_top",
        on_click=controller.restart_slider,
    )

    if not st.session_state.slider_over:
        level = st.session_state.slider_level
        question = st.session_state.slider_question
        st.caption(f"Current Level {level}")
        st.info(question["question"])
        st.caption(
            f"Subject: {question['game']}"
        )
        st.button(
            "🛑 STOP SLIDER (LMB)",
            key=f"slider_stop_button_{level}",
            on_click=controller.lock_slider,
            width="stretch",
        )
        render_active_slider()
        if st.session_state.slider_msg:
            st.success(st.session_state.slider_msg)
    else:
        render_slider_game_over()



def draw_cipher_columns():
    elapsed = controller.bit_fit_reveal_elapsed()
    columns = st.columns(st.session_state.bf_cols)
    for index, column in enumerate(columns):
        active = st.session_state.bf_active[index]
        if st.session_state.bf_space_columns[index]:
            column.markdown("### ")
            continue
        if not active:
            column.markdown("### -")
        else:
            displayed_text = bit_fit.displayed_hint(
                elapsed,
                st.session_state.bf_answer_reveal_stages[index],
                st.session_state.bf_answer_letters[index],
            )
            column.markdown(f"### {displayed_text}")

        column.button(
            st.session_state.bf_player[index],
            key=f"bf_cycle_{index}",
            on_click=controller.cycle_letter,
            args=(index,),
            disabled=not active or st.session_state.bf_over,
            width="stretch",
        )
        if active:
            next_choice = bit_fit.get_next_choice(
                st.session_state.bf_options,
                st.session_state.bf_player,
                index,
            )
            column.caption(f"**{next_choice}**", text_alignment="center")


@st.fragment(run_every=bit_fit.BIT_FIT_REFRESH_SECONDS)
def render_live_bit_fit():
    st.metric(
        "",
        timer.format_time(controller.get_elapsed("bit_fit")),
    )
    draw_cipher_columns()


def render_bit_fit_page():
    st.write("# 💻 Bit Fit Minigame")
    st.caption(
        "Decode the characters one by one."
    )

    save_data = get_save_data()
    controller.ensure_bit_fit_ready()

    if st.session_state.get("game_result_ready", False):
        render_game_result("Bit Fit", save_data)
        return
    if not render_start_gate("Bit Fit", "bit_fit"):
        return
    controller.consume_bit_fit_pending_reveal()

    reset_col, score_col, combo_col, restart_col = st.columns([1, 1, 1, 1])
    restart_col.button(
        "Restart Bit Fit",
        on_click=controller.restart_bit_fit,
    )
    reset_col.metric("Round", st.session_state.bf_round)
    score_col.metric("Saved Score", save_data.check_score())
    with combo_col:
        render_combo_status("Combo")

    question = st.session_state.bf_question
    st.info(question["question"])
    st.caption(
        f"Subject: {question['game']}"
    )

    if not st.session_state.bf_over:
        render_live_bit_fit()
        st.button("⚡ Decode Word", on_click=controller.submit_round, width="stretch")
        if st.session_state.bf_msg:
            st.success(st.session_state.bf_msg)
    else:
        render_live_bit_fit()
        st.error(st.session_state.bf_msg)



TERMINAL_MODE = "pills"

TERMINAL_CSS = """
<style>
[class*="st-key-hacking_terminal"] {
    border: 1px solid rgba(148, 163, 184, 0.45);
    border-radius: 0.8rem;
    background: rgba(15, 23, 42, 0.7);
    padding: 0.75rem;
    max-height: 18rem;
    overflow: auto;
    box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.12);
}
[class*="st-key-hacking_terminal"] [data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-wrap: wrap !important;
    justify-content: flex-start !important;
    align-items: center;
    gap: 0.2rem 0.35rem !important;
    min-height: 0.82rem;
    margin: 0;
}
[class*="st-key-hacking_terminal"] [data-testid="stHorizontalBlock"] > div {
    padding: 0;
    margin: 0;
    flex: 0 0 auto;
}
[class*="st-key-hacking_terminal"] button[kind="tertiary"] {
    border: 1px solid rgba(125, 211, 252, 0.25);
    background: rgba(148, 163, 184, 0.08);
    border-radius: 0.35rem;
    box-shadow: none;
    color: #d5e2e8;
    font-family: monospace;
    font-size: 0.76rem;
    line-height: 0.82rem;
    padding: 0.18rem 0.38rem;
    min-height: 0.82rem;
    height: auto;
    margin: 0;
}
[class*="st-key-hacking_terminal"] button[kind="tertiary"]:hover {
    color: #7dd3fc;
    background: rgba(125, 211, 252, 0.12);
    border-color: rgba(125, 211, 252, 0.45);
    text-decoration: none;
}
[class*="st-key-hack_pills"] {
    border: 1px solid rgba(148, 163, 184, 0.45);
    border-radius: 0.8rem;
    background: rgba(15, 23, 42, 0.7);
    padding: 0.75rem;
    max-height: 18rem;
    overflow: auto;
    box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.12);
}
[class*="st-key-hack_pills"] [data-testid="stButtonGroup"] {
    gap: 0.1rem 0.3rem !important;
}
[class*="st-key-hack_pills"] button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0.05rem 0.15rem !important;
    min-height: 0 !important;
    height: auto !important;
    color: #7dd3fc;
}
[class*="st-key-hack_pills"] button * {
    font-family: monospace !important;
    font-size: 0.8rem !important;
    color: inherit !important;
}
[class*="st-key-hack_pills"] button:hover {
    color: #e0f2fe;
    text-decoration: underline;
}
</style>
"""


def render_terminal_buttons():
    round_id = st.session_state.get("hack_round", 0)
    with st.container(
        key=f"hacking_terminal_{round_id}",
        horizontal=True,
        gap=0,
        horizontal_alignment="left",
    ):
        for segment_index, (text, is_word) in enumerate(
            st.session_state.hack_terminal_segments
        ):
            st.button(
                hacking.escape_label(text),
                key=f"hack_segment_{round_id}_{segment_index}",
                type="tertiary",
                on_click=controller.pick_word if is_word else controller.pick_noise,
                args=(text,),
                disabled=st.session_state.hack_over,
                width="content",
            )


def render_terminal_pills():
    round_id = st.session_state.get("hack_round", 0)
    segments = st.session_state.hack_terminal_segments
    st.pills(
        "Terminal dump",
        options=list(range(len(segments))),
        format_func=lambda index: hacking.escape_label(segments[index][0]),
        selection_mode="single",
        key=f"hack_pills_{round_id}",
        on_change=controller.on_terminal_pick,
        disabled=st.session_state.hack_over,
        label_visibility="collapsed",
    )


def render_terminal_dump():
    if TERMINAL_MODE == "pills":
        render_terminal_pills()
    else:
        render_terminal_buttons()


def render_hacking_status_bar(save_data):
    attempts_col, score_col, time_col, combo_col, reset_col = st.columns(
        [1, 1, 1.2, 1, 1]
    )
    reset_col.button(
        "Reset Terminal",
        on_click=controller.restart_hacking,
        disabled=not st.session_state.hack_over,
    )
    attempts_col.metric(
        "Attempts Left",
        f"{st.session_state.hack_attempts}/{len(st.session_state.hack_words) - 1}",
    )
    score_col.metric("Saved Score", save_data.check_score())
    with time_col:
        with st.container(key="hacking_timer_slot"):
            render_timer_display("hacking", label="Decryption Time")
    with combo_col:
        render_combo_status("Combo")


def render_hacking_query_panel():
    st.markdown("#### 📋 Terminal Query:")
    question = st.session_state.hack_question
    st.caption("Question")
    st.success(question["question"])
    st.caption(f"Context: {question['game']}")
    st.info(
        "**Legend**:\n"
        "- Letter : `Exact match (correct position)`\n"
        "- / : `Character exists (wrong position)`\n"
        "- - : `Character absent`"
    )
    for word, feedback in reversed(st.session_state.hack_log):
        st.code(f"> {word} -> FEEDBACK: {feedback}")


def render_hacking_notice():
    notice = st.session_state.get("hack_notice")
    if not notice:
        return
    kind = st.session_state.get("hack_notice_kind", "info")
    if kind == "success":
        st.success(notice)
    elif kind == "error":
        st.error(notice)
    else:
        st.info(notice)


def render_hacking_game(save_data):
    st.write("# 🔐 Terminal Hacking Minigame")
    st.caption("Parse the key within the terminal.")

    controller.prepare_hacking()

    if st.session_state.get("game_result_ready", False):
        render_game_result("Hacking", save_data)
        return
    if not st.session_state.get("game_start_active", False):
        render_start_gate("Hacking", "hacking")
        return

    render_hacking_status_bar(save_data)

    main_col, log_col = st.columns([1.2, 1])
    with main_col:
        st.markdown("#### ▒ Data Noise Terminal Line")
        render_terminal_dump()
    with log_col:
        render_hacking_query_panel()

    render_hacking_notice()


def render_hacking_page():
    st.markdown(TERMINAL_CSS, unsafe_allow_html=True)
    save_data = get_save_data()

    with st.container(key="hacking_root"):
        render_hacking_game(save_data)