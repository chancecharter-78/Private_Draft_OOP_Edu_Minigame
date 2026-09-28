import csv
from io import StringIO
from pathlib import Path

import streamlit as st
from nierva_save_data import QUESTION_DATABASE_PATH

DATABASE_PATH = QUESTION_DATABASE_PATH
REQUIRED_COLUMNS = (
	"game",
	"question",
	"correct answer",
	"wrong answer 1",
	"wrong answer 2",
	"wrong answer 3",
	"difficulty",
)
OPTIONAL_COLUMNS = ()


def get_schema():
	return {
		"required_columns": REQUIRED_COLUMNS,
		"optional_columns": OPTIONAL_COLUMNS,
	}


def validate_csv(csv_text: str) -> tuple[bool, str]:
	try:
		rows = list(csv.reader(StringIO(csv_text), strict=True))
	except csv.Error as error:
		return False, f"Invalid CSV syntax: {error}"

	rows = [row for row in rows if row]
	if not rows:
		return False, "Enter a CSV header and at least one data row."

	headers = [header.strip().lower() for header in rows[0]]
	if any(not header for header in headers):
		return False, "Column headers cannot be blank."
	if len(headers) != len(set(headers)):
		return False, "Column headers must be unique."

	missing = set(REQUIRED_COLUMNS) - set(headers)
	if missing:
		return False, f"Missing required columns: {', '.join(sorted(missing))}."

	required_indexes = [headers.index(column) for column in REQUIRED_COLUMNS]
	for line_number, row in enumerate(rows[1:], start=2):
		if len(row) != len(headers):
			return False, f"Row {line_number} has {len(row)} fields; expected {len(headers)}."
		if any(not row[index].strip() for index in required_indexes):
			return False, f"Row {line_number} is missing a required value."

	if len(rows) == 1:
		return False, "Add at least one data row below the header."
	return True, f"CSV is valid: {len(rows) - 1} data row(s), {len(headers)} column(s)."


def load_database(file_path: Path = DATABASE_PATH) -> str:
	if not file_path.exists():
		return get_output_format()
	return file_path.read_text(encoding="utf-8-sig")


def save_database(csv_text: str, file_path: Path = DATABASE_PATH) -> None:
	is_valid, message = validate_csv(csv_text)
	if not is_valid:
		raise ValueError(message)
	file_path.write_text(csv_text, encoding="utf-8")


def get_ai_guidelines() -> str:
	return (
		"Create one educational challenge per row. Include the game, a concise question, "
		"one correct answer, three distinct wrong answers, and a difficulty. "
		"Return raw CSV with the required header; "
		"quote fields that contain commas, quotation marks, or line breaks."
	)


def get_output_format() -> str:
	return "game,question,correct answer,wrong answer 1,wrong answer 2,wrong answer 3,difficulty\n"


def main():
	st.title("CSV Content Database")
	st.caption("Type or paste CSV content, validate it, and save the database locally.")

	schema = get_schema()
	schema_description = "Required columns: " + ", ".join(schema["required_columns"])
	if schema["optional_columns"]:
		schema_description += ". Optional: " + ", ".join(schema["optional_columns"])
	schema_description += ". Extra columns are allowed."
	st.caption(schema_description)

	if "csv_editor_text" not in st.session_state:
		st.session_state.csv_editor_text = load_database()

	uploaded_file = st.file_uploader("Load a CSV file into the editor", type=["csv"])
	if uploaded_file is not None and st.button("Use uploaded file"):
		try:
			st.session_state.csv_editor_text = uploaded_file.getvalue().decode("utf-8-sig")
			st.rerun()
		except UnicodeDecodeError:
			st.error("The uploaded file must be UTF-8 encoded.")

	csv_text = st.text_area(
		"CSV content",
		key="csv_editor_text",
		height=360,
		placeholder=get_output_format(),
	)

	validate_col, save_col = st.columns(2)
	if validate_col.button("Validate CSV", use_container_width=True):
		is_valid, message = validate_csv(csv_text)
		if is_valid:
			st.success(message)
			st.dataframe(list(csv.DictReader(StringIO(csv_text))), use_container_width=True)
		else:
			st.error(message)

	if save_col.button("Save Database", use_container_width=True):
		try:
			save_database(csv_text)
			st.success(f"Saved {DATABASE_PATH.name}.")
		except ValueError as error:
			st.error(str(error))

	st.download_button(
		"Download CSV",
		data=csv_text,
		file_name=DATABASE_PATH.name,
		mime="text/csv",
	)

	with st.expander("AI generation guidelines"):
		st.write(get_ai_guidelines())
		st.code(get_output_format(), language="csv")


if __name__ == "__main__":
	main()
