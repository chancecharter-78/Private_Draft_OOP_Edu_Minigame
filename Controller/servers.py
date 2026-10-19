
from datetime import datetime, timezone

import streamlit as st

from Controller.question_sets import list_question_sets
from Model import server
from Repository import server_repository
from Repository.database import DuplicateNameError


def list_servers(username):
    now = datetime.now(timezone.utc)
    return [
        server.build_server_status(
            server_record["id"],
            server_record["name"],
            server_record["is_default"],
            server_record["question_sets"],
            server_record["review_cards"],
            now,
        )
        for server_record in server_repository.fetch_server_overview(
            username.casefold()
        )
    ]


def get_server_status(username, server_id):
    for server in list_servers(username):
        if server["id"] == server_id:
            return server
    raise ValueError("This server is not available to this account.")


def create_server(username):
    return server_repository.insert_next_server(
        username.casefold(),
        server.next_server_name,
    )


def rename_server(username, server_id, name):
    server_name, error = server.validate_server_name(name)
    if error:
        return False, error
    try:
        renamed = server_repository.rename_server(
            username.casefold(),
            server_id,
            server_name,
        )
    except DuplicateNameError:
        return False, "A server with that name already exists."
    if not renamed:
        return False, "This server is not available to this account."
    return True, ""


def get_server_question_set_ids(username, server_id):
    return server_repository.get_server_question_set_ids(
        username.casefold(),
        server_id,
    )


def set_server_question_sets(username, server_id, question_set_ids):
    selected_ids = list(dict.fromkeys(question_set_ids))
    if any(type(set_id) is not int for set_id in selected_ids):
        raise ValueError("Question-set IDs must be integers.")
    return server_repository.replace_server_question_sets(
        username.casefold(),
        server_id,
        selected_ids,
    )


def delete_server(username, server_id):
    return server_repository.delete_server(username.casefold(), server_id)



def open_server(server_id):
    st.session_state.selected_server_id = server_id
    st.session_state.page = "Server menu"


def add_server(username):
    server_id, _ = create_server(username)
    open_server(server_id)


def return_to_server_list():
    st.session_state.page = "Servers"


def save_server_question_sets_on_change(username, server_id, selection_key):
    if not set_server_question_sets(
        username,
        server_id,
        st.session_state[selection_key],
    ):
        raise ValueError("This server is not available to this account.")


def toggle_server_rename(server_id):
    open_key = f"rename_server_open_{server_id}"
    st.session_state[open_key] = not st.session_state.get(open_key, False)


def save_server_name_on_click(username, server_id, name_key, open_key):
    renamed, message = rename_server(
        username,
        server_id,
        st.session_state[name_key],
    )
    if renamed:
        st.session_state[open_key] = False
        st.session_state[f"server_name_notice_{server_id}"] = (
            "success",
            "Server name updated.",
        )
    else:
        st.session_state[f"server_name_notice_{server_id}"] = ("error", message)


def cancel_server_rename(server_id, name_key, open_key):
    st.session_state.pop(name_key, None)
    st.session_state[open_key] = False


def request_server_delete():
    st.session_state.server_delete_confirmation_open = True


def cancel_server_delete():
    st.session_state.server_delete_confirmation_open = False


def decommission_server(username, server_id, server_name):
    if not delete_server(username, server_id):
        return False
    st.session_state.pop(f"server_question_sets_{server_id}", None)
    st.session_state.pop(f"server_name_{server_id}", None)
    st.session_state.pop(f"rename_server_open_{server_id}", None)
    st.session_state.pop(f"server_name_notice_{server_id}", None)
    st.session_state.pop("selected_server_id", None)
    st.session_state.server_delete_confirmation_open = False
    st.session_state.page = "Servers"
    st.session_state.server_delete_notice = f"{server_name} has been deleted."
    return True
