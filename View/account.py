
import streamlit as st

from Controller import account as controller


def sign_in():
    st.title("Account Login", text_alignment="center")
    st.header("Welcome to Voiding Boredom V3.1 Alpha!")
    st.caption("Create an account or sign in to save your game progress.")
    st.session_state.setdefault("auth_view", "login")

    if st.session_state.auth_view == "login":
        with st.form("returning_player"):
            st.text_input("Username", key="login_username", max_chars=20)
            st.text_input(
                "Password",
                type="password",
                key="login_password",
                max_chars=128,
            )
            login_col, register_col = st.columns(2)
            with login_col:
                st.form_submit_button("Log In", on_click=controller.log_in)
            with register_col, st.container(
                horizontal=True,
                horizontal_alignment="right",
            ):
                st.form_submit_button(
                    "Register now",
                    on_click=controller.switch_auth_view,
                    type="tertiary",
                    args=("register",),
                )
    else:
        with st.form("new_player"):
            st.text_input("Username", key="new_username", max_chars=20)
            st.text_input(
                "Password (at least 8 characters)",
                type="password",
                key="new_password",
                max_chars=128,
            )
            create_col, login_col = st.columns(2)
            with create_col:
                st.form_submit_button("Create account", on_click=controller.create_account)
            with login_col, st.container(
                horizontal=True,
                horizontal_alignment="right",
            ):
                st.form_submit_button(
                    "Already have an account? Log In",
                    type="tertiary",
                    on_click=controller.switch_auth_view,
                    args=("login",),
                )

    if st.session_state.get("auth_error"):
        st.error(st.session_state.auth_error)


@st.dialog("Sign out?")
def confirm_sign_out():
    st.write("Are you sure you want to sign out of this account?")
    cancel_col, confirm_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", key="cancel_sign_out"):
            controller.cancel_sign_out()
            st.rerun()
    with confirm_col:
        if st.button("Sign out", key="confirm_sign_out", type="primary"):
            controller.sign_out()
            st.rerun()
