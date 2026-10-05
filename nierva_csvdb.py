import streamlit as st

from nierva_save_data import (
    REQUIRED_COLUMNS,
    delete_question_set,
    get_question_set_csv,
    list_question_sets,
    save_question_set,
    set_active_question_set,
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


def get_ai_prompt():
    return (
        "Create educational quiz questions as raw CSV only. Use exactly this header:\n"
        "game,question,correct answer,wrong answer 1,wrong answer 2,"
        "wrong answer 3,difficulty\n\n"
        "Add one question per row. Include a subject in game, a concise question, "
        "one correct answer, three different wrong answers, and a difficulty "
        "(for example Easy, Medium, or Hard). Every answer must be a distinct "
        "A-Z word with no spaces, numbers, or symbols and no more than 12 letters. "
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


def main():
    st.title("📚 My Question Sets")
    st.caption(
        "Your question sets are private to your account. Download a CSV to share a copy "
        "with another player."
    )
    with st.expander("CSV format and AI prompt"):
        st.markdown("Use this exact header followed by one question per row:")
        st.code(get_csv_template(), language="csv")
        st.markdown("Copy this prompt into an AI tool to generate a compatible CSV:")
        st.code(get_ai_prompt(), language="text")

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

    with st.form("upload_question_set"):
        st.subheader("Add a question set")
        set_name = st.text_input("Question set name", max_chars=60)
        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
        submitted = st.form_submit_button("Save and use this question set")

    if submitted:
        if uploaded_file is None:
            st.error("Choose a CSV file to upload.")
        else:
            try:
                uploaded_csv = uploaded_file.getvalue().decode("utf-8-sig")
                _, message = save_question_set(username, set_name, uploaded_csv)
                if message:
                    st.error(message)
                else:
                    st.success("Question set saved.")
                    st.rerun()
            except UnicodeDecodeError:
                st.error("The CSV file must be UTF-8 encoded.")
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
