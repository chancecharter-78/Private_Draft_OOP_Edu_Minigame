import streamlit as st
import random
import nierva_timer

MAX_SLIDER_BARS = 5

def init_slider():
    st.session_state.slider_level = 1
    st.session_state.slider_score = 0
    st.session_state.slider_history = []
    st.session_state.slider_position = 50
    st.session_state.slider_direction = 1
    st.session_state.slider_over = False
    st.session_state.slider_msg = ""
    nierva_timer.start_timer("slider")
    green_size = max(10, 40 - (st.session_state.slider_level * 5))
    green_start = random.randint(10, 90 - green_size)
    st.session_state.green_range = (green_start, green_start + green_size)

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
    g_start, g_end = st.session_state.green_range
    pos = st.session_state.slider_position
    if g_start <= pos <= g_end:
        st.session_state.slider_history.append({
            'level': st.session_state.slider_level,
            'green_range': st.session_state.green_range,
            'position': pos,
        })
        st.session_state.slider_history = st.session_state.slider_history[-(MAX_SLIDER_BARS - 1):]
        st.session_state.slider_score += 100
        st.session_state.slider_level += 1
        st.session_state.slider_position = 50
        st.session_state.slider_direction = 1
        st.session_state.slider_msg = f"✅ Cleared Level {st.session_state.slider_level - 1}! Target zone narrowed."
        green_size = max(8, 40 - (st.session_state.slider_level * 5))
        green_start = random.randint(10, 90 - green_size)
        st.session_state.green_range = (green_start, green_start + green_size)
    else:
        st.session_state.slider_over = True
        elapsed = nierva_timer.stop_timer("slider")
        st.session_state.slider_msg = f"❌ Failed! Stopped in red section. Game Over! Duration: {nierva_timer.format_time(elapsed)}"

def render_slider_bar(g_start, g_end, pos):
    track_html = f"""
    <div style="position: relative; width: 100%; height: 40px; background-color: #ff3333; border-radius: 6px; overflow: hidden; margin: 15px 0;">
        <div style="position: absolute; left: {g_start}%; width: {g_end - g_start}%; height: 100%; background-color: #00cc44;"></div>
        <div style="position: absolute; left: {pos}%; top: 0; width: 8px; height: 100%; background-color: #ffffff; border: 2px solid #000; transform: translateX(-50%);"></div>
    </div>
    """
    st.markdown(track_html, unsafe_allow_html=True)

def main():
    st.write('# 🎚️ Slider Precision Minigame')
    st.caption('Timing mechanics prototype: Stop the marker inside the green zone.')

    if 'slider_level' not in st.session_state or 'slider_history' not in st.session_state:
        init_slider()

    c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1])
    c1.metric('Level', st.session_state.slider_level)
    c2.metric('Score', st.session_state.slider_score)
    with c3:
        nierva_timer.render_timer_display("slider", label="Game Time")
    if c4.button('New Game'):
        init_slider()

    for completed_bar in st.session_state.slider_history:
        st.caption(f"Completed Level {completed_bar['level']}")
        g_start, g_end = completed_bar['green_range']
        render_slider_bar(g_start, g_end, completed_bar['position'])

    st.caption(f"Current Level {st.session_state.slider_level}")
    g_start, g_end = st.session_state.green_range
    render_slider_bar(g_start, g_end, st.session_state.slider_position)

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
