
import streamlit as st

from Model import question_set
from Model.account import (
    clean_password,
    clean_username,
    create_credentials,
    random_server_name,
    verify_password,
)
from Model.player import GameSaveData
from Repository import player_repository, question_set_repository


def register_player(username, password):
    name = clean_username(username)
    password = clean_password(password)
    salt_hex, hash_hex = create_credentials(password)
    starter_csv = question_set_repository.load_starter_csv()
    question_set.parse_question_csv(starter_csv)

    created = player_repository.create_player(
        name.casefold(),
        name,
        salt_hex,
        hash_hex,
        starter_csv,
        random_server_name(),
    )
    if not created:
        return None, "Username already exists, please try another."

    return GameSaveData(player_name=name), ""


def authenticate_player(username, password):
    try:
        name = clean_username(username)
        password = clean_password(password)
    except ValueError:
        return None

    key = name.casefold()
    row = player_repository.get_credentials(key)
    if row is None:
        return None

    saved_name, salt, saved_hash, score, completed_rounds = row
    if not salt or not saved_hash:
        return None
    if not verify_password(password, salt, saved_hash):
        return None

    history = player_repository.get_clear_history(key)
    return GameSaveData(
        player_name=saved_name,
        starting_score=score,
        completed_rounds=completed_rounds,
        history=[
            {"game": game, "level": level, "points": points, "details": details}
            for game, level, points, details in history
        ],
    )



def switch_auth_view(view):
    st.session_state.auth_view = view
    st.session_state.auth_error = ""


def create_account():
    try:
        username = clean_username(st.session_state.new_username)
        save_data, message = register_player(
            username,
            st.session_state.new_password,
        )
        st.session_state.new_password = ""
        if save_data is None:
            st.session_state.auth_error = message
            return
        start_session(username, save_data)
    except ValueError as error:
        st.session_state.new_password = ""
        st.session_state.auth_error = str(error)
    except RuntimeError as error:
        st.session_state.new_password = ""
        st.session_state.auth_error = str(error)


def log_in():
    try:
        save_data = authenticate_player(
            st.session_state.login_username,
            st.session_state.login_password,
        )
    except RuntimeError as error:
        st.session_state.login_password = ""
        st.session_state.auth_error = str(error)
        return
    st.session_state.login_password = ""
    if save_data is None:
        st.session_state.auth_error = "Username or password is incorrect."
        return
    start_session(save_data.player_name, save_data)


def start_session(username, save_data):
    st.session_state["new_password"] = ""
    st.session_state["login_password"] = ""
    st.session_state.username = username
    st.session_state.save_data = save_data
    st.session_state.page = "Homepage"
    st.session_state.auth_error = ""


def sign_out():
    st.session_state.clear()


def request_sign_out():
    st.session_state.sign_out_confirmation_open = True


def cancel_sign_out():
    st.session_state.sign_out_confirmation_open = False
