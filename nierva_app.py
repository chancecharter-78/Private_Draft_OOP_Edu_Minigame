import streamlit as st
import nierva_home
import nierva_about
import nierva_source
import nierva_slider
import nierva_bit_fit
import nierva_hacking

def init():
    st.session_state.page = 'Homepage'
    st.session_state.project = False
    st.session_state.game = False

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
    }
    curr_page = st.session_state.get('page', 'Homepage')
    if curr_page in pages:
        pages[curr_page]()
    else:
        nierva_home.main()

def set_page(loc=None, reset=False):
    if not st.session_state.get('page') == 'Homepage':
        for key in list(st.session_state.keys()):
            if key not in ('page', 'project', 'game', 'pages', 'set'):
                st.session_state.pop(key)

    if loc:
        st.session_state.page = loc
    else:
        st.session_state.page = st.session_state.get('set', 'Homepage')

    if reset:
        st.session_state.project = False
    elif st.session_state.page in ('About me', 'Source'):
        st.session_state.project = True
        st.session_state.game = False

def change_button():
    set_page('Slider')
    st.session_state.game = True
    st.session_state.project = True

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

        if st.session_state.get('page') == 'Homepage':
            st.image('https://c.tenor.com/-420uI8y-RkAAAAd/anime-welcome.gif')

    load_page()

if __name__ == '__main__':
    main()
