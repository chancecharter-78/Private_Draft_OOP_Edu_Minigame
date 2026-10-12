from pathlib import Path

import streamlit as st

from nierva_save_data import (
    REQUIRED_COLUMNS,
    delete_question_set,
    get_question_set_csv,
    list_question_sets,
    save_question_set,
    set_active_question_set,
    update_question_set,
    validate_question_csv,
)


def get_schema():
    return {"required_columns": REQUIRED_COLUMNS, "optional_columns": ()}


def get_csv_template():
    return (
        "game,question,correct answer,wrong answer 1,wrong answer 2,"
        "wrong answer 3,difficulty\n"
        "Science,Which planet is known as the Red Planet?,MARS,VENUS,"
        "JUPITER,MERCURY,Easy\n"
    )


def get_csv_example():
    return [
        {"CSV field": "game", "Example": "Science"},
        {"CSV field": "question", "Example": "Which planet is known as the Red Planet?"},
        {"CSV field": "correct answer", "Example": "MARS"},
        {"CSV field": "wrong answer 1", "Example": "VENUS"},
        {"CSV field": "wrong answer 2", "Example": "JUPITER"},
        {"CSV field": "wrong answer 3", "Example": "MERCURY"},
        {"CSV field": "difficulty", "Example": "Easy"},
    ]


def get_ai_prompt():
    return (
        "Create educational quiz questions as raw CSV only. Use these columns "
        "in this exact order:\n"
        "- game\n"
        "- question\n"
        "- correct answer\n"
        "- wrong answer 1\n"
        "- wrong answer 2\n"
        "- wrong answer 3\n"
        "- difficulty\n\n"
        "Add one question per row. Include a subject in game, a concise question, "
        "one correct answer, three different wrong answers, and a difficulty "
        "(for example Easy, Medium, or Hard). Every answer must be a distinct "
        "answer of no more than 32 characters using A-Z letters, 0-9 numbers, "
        "spaces, and periods. Bit Fit treats spaces as word breaks. "
        "Quote any CSV field containing commas, quotation marks, or line breaks. "
        "Do not include markdown fences or text outside the CSV."
    )


def validate_csv(csv_text):
    return validate_question_csv(csv_text)


def set_active_set(state_key):
    set_active_question_set(
        st.session_state.username,
        st.session_state[state_key],
    )


def format_editor_target(set_id, names_by_id):
    return "New question set" if set_id is None else names_by_id[set_id]


def main():
    st.title("📚 My Question Sets")
    st.caption(
        "Your question sets are private to your account. Download a CSV to share a copy "
        "with another player."
    )
    with st.expander("CSV format and AI prompt"):
        st.markdown(
            "Each row in the CSV must use these columns in order. "
            "This example is shown as a table so long fields remain easy to read:"
        )
        st.dataframe(get_csv_example(), hide_index=True, width="stretch")
        st.download_button(
            "Download CSV template",
            data=get_csv_template(),
            file_name="question_template.csv",
            mime="text/csv",
            width="stretch",
        )
        st.markdown(
            "Restrictions:\n"
            "- Include every required column in the header.\n"
            "- Give each question one correct answer and three different wrong answers.\n"
            "- Answers may contain A-Z letters, 0-9 numbers, spaces, and periods.\n"
            "- Each answer can be at most 32 characters long.\n"
            "- Bit Fit treats spaces as word breaks; numbers and periods are selectable.\n"
            "- Quote CSV fields that contain commas, quotes, or line breaks.\n"
            "- Use one question per row."
        )
        st.markdown("Copy this prompt into an AI tool to generate a compatible CSV:")
        st.code(get_ai_prompt(), language="text", wrap_lines=True)

    username = st.session_state.username
    question_sets = list_question_sets(username)
    if not question_sets:
        st.error("This account does not have a question set yet.")
        return

    names_by_id = {item["id"]: item["name"] for item in question_sets}
    active_set = next(item for item in question_sets if item["active"])
    state_key = f"question_set_{active_set['id']}"
    selected_id = st.selectbox(
        "Active question set",
        options=list(names_by_id),
        index=list(names_by_id).index(active_set["id"]),
        format_func=lambda set_id: names_by_id[set_id],
        key=state_key,
        on_change=set_active_set,
        args=(state_key,),
    )

    csv_text = get_question_set_csv(username, selected_id)
    st.download_button(
        "Download a copy",
        data=csv_text,
        file_name=f"{names_by_id[selected_id]}.csv",
        mime="text/csv",
        width="stretch",
    )

    if "question_editor_target" not in st.session_state:
        st.session_state.question_editor_target = active_set["id"]
    if st.session_state.question_editor_target not in (
        None,
        *names_by_id.keys(),
    ):
        st.session_state.question_editor_target = active_set["id"]
    if "question_editor_loaded_id" not in st.session_state:
        st.session_state.question_editor_loaded_id = active_set["id"]
        st.session_state.question_editor_csv = get_question_set_csv(
            username,
            active_set["id"],
        )
        st.session_state.question_editor_name = active_set["name"]

    upload_tab, editor_tab = st.tabs(["Upload CSV", "Paste or edit CSV"])
    with upload_tab:
        st.subheader("Load a CSV file into the editor")
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv"],
            key="question_set_upload_file",
        )
        if st.button("Load file into editor", disabled=uploaded_file is None):
            if uploaded_file is not None:
                try:
                    st.session_state.question_editor_csv = (
                        uploaded_file.getvalue().decode("utf-8-sig")
                    )
                    st.session_state.question_editor_name = Path(
                        uploaded_file.name
                    ).stem
                    st.session_state.question_editor_target = None
                    st.session_state.question_editor_loaded_id = None
                    st.session_state.question_editor_notice = (
                        "CSV loaded. Review or edit it in the Paste or edit CSV tab, "
                        "then save it."
                    )
                    st.session_state.question_editor_notice_type = "info"
                except UnicodeDecodeError:
                    st.error("The CSV file must be UTF-8 encoded.")
        st.download_button(
            "Download CSV template",
            data=get_csv_template(),
            file_name="question_template.csv",
            mime="text/csv",
        )

    with editor_tab:
        target_id = st.selectbox(
            "Editing",
            options=[None, *names_by_id],
            format_func=lambda set_id: format_editor_target(set_id, names_by_id),
            key="question_editor_target",
        )
        if st.session_state.question_editor_loaded_id != target_id:
            if target_id is None:
                st.session_state.question_editor_csv = get_csv_template()
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
        is_valid, validation_message = validate_csv(
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
            try:
                if target_id is None:
                    saved_id, message = save_question_set(
                        username,
                        st.session_state.question_editor_name,
                        st.session_state.question_editor_csv,
                    )
                    if saved_id is None:
                        st.error(message)
                    else:
                        st.session_state.question_editor_target = saved_id
                        st.session_state.question_editor_loaded_id = saved_id
                        st.session_state.question_editor_notice = (
                            "Question set saved and activated."
                        )
                        st.session_state.question_editor_notice_type = "success"
                        st.rerun()
                else:
                    updated, message = update_question_set(
                        username,
                        target_id,
                        st.session_state.question_editor_name,
                        st.session_state.question_editor_csv,
                    )
                    if not updated:
                        st.error(message)
                    else:
                        st.session_state.question_editor_notice = (
                            "Question set changes saved."
                        )
                        st.session_state.question_editor_notice_type = "success"
                        st.rerun()
            except ValueError as error:
                st.error(str(error))

    other_sets = [item for item in question_sets if not item["active"]]
    if other_sets:
        st.subheader("Remove a question set")
        removable_ids = [item["id"] for item in other_sets]
        delete_id = st.selectbox(
            "Saved question set",
            options=removable_ids,
            format_func=lambda set_id: names_by_id[set_id],
            key="delete_question_set_id",
        )
        if st.button("Delete question set"):
            if delete_question_set(username, delete_id):
                st.success("Question set deleted.")
                st.rerun()
            else:
                st.error("The active question set cannot be deleted.")


if __name__ == "__main__":
    main()
