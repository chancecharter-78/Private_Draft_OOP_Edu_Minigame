
import streamlit as st

from Controller import account, navigation as controller


def draw_style():
    st.set_page_config(
        page_title="Voiding Boredom V3.1 Prototype",
        page_icon="🎮",
        layout="centered",)
    st.markdown(
        """
        <style>
            header {visibility: visible;}
            footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    with st.sidebar:
        if st.session_state.page in {"Servers", "Server menu"}:
            st.button(
                "🏠 Homepage",
                on_click=controller.set_page,
                args=("Homepage", True),
                width="stretch",
            )
        else:
            st.button(
                "🖥 Servers",
                on_click=controller.show_servers,
                width="stretch",
            )

        about_col, source_col = st.columns(2)
        about_col.button(
            "🧑‍💻 Myself",
            on_click=controller.set_page,
            args=("About me",),
            width="stretch",
        )
        source_col.button(
            "📁 Source",
            on_click=controller.set_page,
            args=("Source",),
            width="stretch",
        )
        st.button(
            "🏆 Leaderboard",
            on_click=controller.set_page,
            args=("Leaderboard",),
            width="stretch",
        )
        st.button(
            "📚 Question Set Browser",
            on_click=controller.set_page,
            args=("Question Sets",),
            width="stretch",
        )
        if st.button(
            "Sign out",
            width="stretch",
        ):
            account.request_sign_out()
