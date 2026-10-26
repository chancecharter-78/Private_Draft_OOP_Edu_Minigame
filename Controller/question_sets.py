
from pathlib import Path

import streamlit as st

from Model import question_set
from Repository import question_set_repository
from Repository.database import DuplicateNameError


def list_question_sets(username):
    rows = question_set_repository.list_question_sets(username.casefold())
    return [
        {"id": set_id, "name": name, "active": bool(active)}
        for set_id, name, active in rows
    ]


def get_question_set_csv(username, set_id=None):
    csv_text = question_set_repository.get_question_set_csv(
        username.casefold(),
        set_id,
    )
    if csv_text is None:
        raise ValueError("This question set is not available to this account.")
    return csv_text


def save_question_set(username, name, csv_text):
    set_name = name.strip()
    error = question_set.validate_set_name(set_name)
    if error:
        return None, error
    question_set.parse_question_csv(csv_text)

    try:
        set_id = question_set_repository.insert_question_set(
            username.casefold(),
            set_name,
            csv_text,
        )
    except DuplicateNameError:
        return None, "A question set with that name already exists."
    return set_id, ""


def update_question_set(username, set_id, name, csv_text):
    set_name = name.strip()
    error = question_set.validate_set_name(set_name)
    if error:
        return False, error
    question_set.parse_question_csv(csv_text)

    try:
        updated = question_set_repository.update_question_set(
            username.casefold(),
            set_id,
            set_name,
            csv_text,
        )
    except DuplicateNameError:
        return False, "A question set with that name already exists."
    if not updated:
        return False, "This question set is not available to this account."
    return True, ""


def set_active_question_set(username, set_id):
    return question_set_repository.set_active_question_set(
        username.casefold(),
        set_id,
    )


def delete_question_set(username, set_id):
    return question_set_repository.delete_question_set(
        username.casefold(),
        set_id,
    )



def delete_question_set_on_click(username, set_id):
    if delete_question_set(username, set_id):
        st.session_state.pop("delete_question_set_id", None)
        st.session_state.pop("confirm_delete_question_set", None)
        st.session_state.question_set_delete_notice = (
            "success",
            "Question set deleted.",
        )
    else:
        st.session_state.question_set_delete_notice = (
            "error",
            "The question set could not be deleted.",
        )


def prepare_editor_state(username, selected_id, names_by_id):
    if "question_editor_pending_target" in st.session_state:
        st.session_state.question_editor_target = st.session_state.pop(
            "question_editor_pending_target"
        )
    if "question_editor_target" not in st.session_state:
        st.session_state.question_editor_target = selected_id
    if st.session_state.question_editor_target not in (
        None,
        *names_by_id.keys(),
    ):
        st.session_state.question_editor_target = selected_id
    if "question_editor_loaded_id" not in st.session_state:
        st.session_state.question_editor_loaded_id = selected_id
        st.session_state.question_editor_csv = get_question_set_csv(
            username,
            selected_id,
        )
        st.session_state.question_editor_name = names_by_id[selected_id]


def load_uploaded_csv(uploaded_file):
    try:
        st.session_state.question_editor_csv = (
            uploaded_file.getvalue().decode("utf-8-sig")
        )
    except UnicodeDecodeError:
        return "The CSV file must be UTF-8 encoded."
    st.session_state.question_editor_name = Path(uploaded_file.name).stem
    st.session_state.question_editor_target = None
    st.session_state.question_editor_loaded_id = None
    st.session_state.question_editor_notice = (
        "CSV loaded. Review or edit it in the Paste or edit CSV tab, "
        "then save it."
    )
    st.session_state.question_editor_notice_type = "info"
    return None


def sync_editor_to_target(username, target_id, names_by_id):
    if st.session_state.question_editor_loaded_id == target_id:
        return
    if target_id is None:
        st.session_state.question_editor_csv = question_set.get_csv_template()
        st.session_state.question_editor_name = ""
    else:
        st.session_state.question_editor_csv = get_question_set_csv(
            username,
            target_id,
        )
        st.session_state.question_editor_name = names_by_id[target_id]
    st.session_state.question_editor_loaded_id = target_id
    st.session_state.question_editor_notice = ""
    st.session_state.question_editor_notice_type = ""


def save_editor(username, target_id):
    if st.session_state.question_editor_loaded_id != target_id:
        return (
            "stale",
            "The selected question set changed before it was loaded. "
            "Please select it again before saving.",
        )
    try:
        if target_id is None:
            saved_id, message = save_question_set(
                username,
                st.session_state.question_editor_name,
                st.session_state.question_editor_csv,
            )
            if saved_id is None:
                return "error", message
            st.session_state.question_editor_pending_target = saved_id
            st.session_state.question_editor_loaded_id = saved_id
            st.session_state.question_editor_notice = (
                "Question set saved. Assign it to a server to use it."
            )
            st.session_state.question_editor_notice_type = "success"
            return "saved", ""

        updated, message = update_question_set(
            username,
            target_id,
            st.session_state.question_editor_name,
            st.session_state.question_editor_csv,
        )
        if not updated:
            return "error", message
        st.session_state.question_editor_notice = "Question set changes saved."
        st.session_state.question_editor_notice_type = "success"
        return "saved", ""
    except ValueError as error:
        return "error", str(error)
