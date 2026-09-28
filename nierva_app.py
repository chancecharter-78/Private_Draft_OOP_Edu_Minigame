import streamlit as st
import nierva_home
import nierva_about
import nierva_source
import nierva_slider
import nierva_bit_fit
import nierva_hacking
import nierva_progression
import nierva_csvdb
from nierva_save_data import GameSaveData

def init():
    st.session_state.page = 'Homepage'
    st.session_state.project = False
    st.session_state.game = False
    if "save_data" not in st.session_state:
        st.session_state.save_data = st.session_state.get("nierva_save_data", GameSaveData())

def draw_style():
    st.set_page_config(page_title="Educational Minigames Prototype", page_icon='🎮', layout='centered')
    style = """
        <style>
            header {visibility: visible;}
            footer {visibility: hidden;}
        </style>
    """
    st.markdown(style, unsafe_allow_html=True)

def load_page():
    pages = {
        'Homepage': nierva_home.main,
        'About me': nierva_about.main,
        'Source': nierva_source.main,
        'Slider': nierva_slider.main,
        'Bit Fit': nierva_bit_fit.main,
        'Hacking': nierva_hacking.main,
        'CSV Database': nierva_csvdb.main,
    }
    curr_page = st.session_state.get('page', 'Homepage')
    if curr_page in pages:
        pages[curr_page]()
    else:
        nierva_home.main()

def set_page(loc=None, reset=False):
    target_page = loc or st.session_state.get('set', 'Homepage')
    if target_page in nierva_progression.GAME_ORDER:
        nierva_progression.start_game(target_page)
        return

    if not st.session_state.get('page') == 'Homepage':
        for key in list(st.session_state.keys()):
            if key not in (
                'page', 'project', 'game', 'pages', 'set', 'save_data',
                'nierva_save_data', 'flow_game', 'flow_clears', 'flow_target',
            ):
                st.session_state.pop(key)

    st.session_state.page = target_page

    if reset:
        st.session_state.project = False
    elif st.session_state.page in ('About me', 'Source', 'CSV Database'):
        st.session_state.project = True
        st.session_state.game = False

def change_button():
    nierva_progression.start_game('Slider')

def main():
    if 'page' not in st.session_state:
        init()

    draw_style()

    with st.sidebar:
        project_col, about_col, source_col = st.columns([1.2, 1, 1])

        if not st.session_state.get('project', False):
            project_col.button('📌 Minigames', on_click=change_button)
        else:
            project_col.button('🏠 Homepage', on_click=set_page, args=('Homepage', True))

        if st.session_state.get('project', False) and st.session_state.get('game', False):
            st.selectbox(
                'Select Minigame Prototype',
                [
                    'Slider',
                    'Bit Fit',
                    'Hacking',
                ],
                key='set',
                on_change=set_page,
            )

        about_col.button('🧑‍💻 Myself', on_click=set_page, args=('About me',))
        source_col.button('📁 Source', on_click=set_page, args=('Source',))
        st.button(
            '🗃️ CSV Database',
            on_click=set_page,
            args=('CSV Database',),
            use_container_width=True,
            disabled=st.session_state.get('page') == 'CSV Database',
        )

        if st.session_state.get('page') == 'Homepage':
            st.image('https://media.tenor.com/WiTP5aZyPLUAAAAi/dice-roll-dice.gif')

    load_page()

if __name__ == '__main__':
    main()