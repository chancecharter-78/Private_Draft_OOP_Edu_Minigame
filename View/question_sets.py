
import streamlit as st

from Controller import question_sets as controller
from Model import question_set


def format_editor_target(set_id, names_by_id):
    return "New question set" if set_id is None else names_by_id[set_id]


def render_help():
    with st.expander("CSV format and AI prompt"):
        st.markdown(
            "Each row in the CSV must use these columns in order. "
            "This example is shown as a table so long fields remain easy to read:"
        )
        st.dataframe(
            question_set.get_csv_example(),
            hide_index=True,
            width="stretch",
        )
        st.download_button(
            "Download CSV template",
            data=question_set.get_csv_template(),
            file_name="question_template.csv",
            mime="text/csv",
            width="stretch",
        )
        st.markdown(
            "Restrictions:\n"
            "- Include every required column in the header.\n"
            "- Give each question one correct answer and three different wrong answers.\n"
            f"- Answers may contain A-Z letters, 0-9 numbers, spaces, and "
            f"{question_set.ANSWER_PUNCTUATION} punctuation.\n"
            "- Each answer can be at most 32 characters long.\n"
            "- Bit Fit keeps spaces as pre-filled inactive columns.\n"
            "- Each active Bit Fit column has one correct choice and two wrong "
            "choices from the same character type.\n"
            "- Quote CSV fields that contain commas, quotes, or line breaks.\n"
            "- Use one question per row."
        )
        st.markdown("Copy this prompt into an AI tool to generate a compatible CSV:")
        st.code(question_set.get_ai_prompt(), language="text", wrap_lines=True)


def render_upload_tab():
    st.subheader("Load a CSV file into the editor")
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        key="question_set_upload_file",
    )
    if st.button("Load File", disabled=uploaded_file is None):
        if uploaded_file is not None:
            error = controller.load_uploaded_csv(uploaded_file)
            if error:
                st.error(error)
    st.download_button(
        "Download CSV template",
        data=question_set.get_csv_template(),
        file_name="question_template.csv",
        mime="text/csv",
    )


def render_editor_tab(username, names_by_id):
    target_id = st.selectbox(
        "Editing",
        options=[None, *names_by_id],
        format_func=lambda set_id: format_editor_target(set_id, names_by_id),
        key="question_editor_target",
    )
    controller.sync_editor_to_target(username, target_id, names_by_id)

    if st.session_state.get("question_editor_notice"):
        if st.session_state.get("question_editor_notice_type") == "success":
            st.success(st.session_state.question_editor_notice)
        else:
            st.info(st.session_state.question_editor_notice)

    st.text_input(
        "Question set name",
        max_chars=60,
        key="question_editor_name",
    )
    st.text_area(
        "CSV content",
        key="question_editor_csv",
        height=360,
        help="Edit or paste the complete CSV, including its header row.",
    )
    is_valid, validation_message = question_set.validate_question_csv(
        st.session_state.question_editor_csv
    )
    if is_valid:
        st.success(validation_message)
    else:
        st.error(validation_message)

    save_label = (
        "Save changes to question set"
        if target_id is not None
        else "Save as new question set"
    )
    if st.button(save_label, type="primary", disabled=not is_valid):
        status, message = controller.save_editor(username, target_id)
        if status == "stale":
            st.error(message)
            st.rerun()
        elif status == "error":
            st.error(message)
        else:
            st.rerun()


def render_delete_section(username, question_sets, names_by_id):
    other_sets = [item for item in question_sets if not item["active"]]
    if not other_sets:
        return
    with st.expander("Delete question set"):
        st.warning(
            "Deleting a question set permanently removes it from every "
            "server and deletes its review history. The active question set "
            "cannot be deleted."
        )
        removable_ids = [item["id"] for item in other_sets]
        delete_id = st.selectbox(
            "Saved question set",
            options=removable_ids,
            format_func=lambda set_id: names_by_id[set_id],
            key="delete_question_set_id",
        )
        confirm_key = "confirm_delete_question_set"
        confirmed = st.checkbox(
            "I understand; delete this question set",
            key=confirm_key,
        )
        if st.button(
            "Delete question set",
            key="delete_question_set",
            disabled=not confirmed,
            on_click=controller.delete_question_set_on_click,
            args=(username, delete_id),
        ):
            st.rerun()


def main():
    st.title("📚 My Question Sets")
    delete_notice = st.session_state.pop("question_set_delete_notice", None)
    if delete_notice:
        if delete_notice[0] == "success":
            st.success(delete_notice[1])
        else:
            st.error(delete_notice[1])
    st.caption(
        "Your question sets are private to your account. Download a CSV to share a copy "
        "with another player."
    )
    render_help()

    username = st.session_state.username
    question_sets = controller.list_question_sets(username)
    if not question_sets:
        st.error("This account does not have a question set yet.")
        return

    names_by_id = {item["id"]: item["name"] for item in question_sets}
    selected_id = st.selectbox(
        "Browse question sets",
        options=list(names_by_id),
        format_func=lambda set_id: names_by_id[set_id],
        key="question_set_browse_id",
    )

    csv_text = controller.get_question_set_csv(username, selected_id)
    st.download_button(
        "Download a copy",
        data=csv_text,
        file_name=f"{names_by_id[selected_id]}.csv",
        mime="text/csv",
        width="stretch",
    )

    controller.prepare_editor_state(username, selected_id, names_by_id)

    upload_tab, editor_tab = st.tabs(["Upload CSV", "Paste or edit CSV"])
    with upload_tab:
        render_upload_tab()
    with editor_tab:
        render_editor_tab(username, names_by_id)

    render_delete_section(username, question_sets, names_by_id)


if __name__ == "__main__":
    main()
