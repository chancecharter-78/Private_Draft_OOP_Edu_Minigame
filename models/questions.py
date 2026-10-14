"""Question CSV parsing and validation rules."""

import csv
from io import StringIO


REQUIRED_COLUMNS = (
    "game",
    "question",
    "correct answer",
    "wrong answer 1",
    "wrong answer 2",
    "wrong answer 3",
    "difficulty",
)
ANSWER_COLUMNS = (
    "correct answer",
    "wrong answer 1",
    "wrong answer 2",
    "wrong answer 3",
)
MAX_ANSWER_LENGTH = 32
QUESTION_REVIEW_MIGRATION_MESSAGE = (
    "Question review scheduling is not set up in the database. Run "
    "supabase/migrations/20261014000000_create_question_review_cards.sql "
    "in the Supabase SQL Editor, then retry."
)


def parse_question_csv(csv_text):
    try:
        rows = [row for row in csv.reader(StringIO(csv_text), strict=True) if row]
    except csv.Error as error:
        raise ValueError(f"Invalid CSV syntax: {error}") from error

    if len(rows) < 2:
        raise ValueError("Enter a CSV header and at least one data row.")

    headers = [header.strip().lower() for header in rows[0]]
    if any(not header for header in headers):
        raise ValueError("Column headers cannot be blank.")
    if len(headers) != len(set(headers)):
        raise ValueError("Column headers must be unique.")

    missing = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}.")

    questions = []
    for line_number, values in enumerate(rows[1:], start=2):
        if len(values) != len(headers):
            raise ValueError(
                f"Row {line_number} has {len(values)} fields; expected {len(headers)}."
            )

        row = dict(zip(headers, (value.strip() for value in values)))
        if any(not row[column] for column in REQUIRED_COLUMNS):
            raise ValueError(f"Row {line_number} is missing a required value.")

        answers = [row[column].upper() for column in ANSWER_COLUMNS]
        if any(len(answer) > MAX_ANSWER_LENGTH for answer in answers):
            raise ValueError(
                f"Row {line_number} has an answer longer than "
                f"{MAX_ANSWER_LENGTH} characters."
            )
        if any(
            not answer.isascii()
            or any(
                not (character.isalnum() or character in " .")
                for character in answer
            )
            for answer in answers
        ):
            raise ValueError(
                f"Row {line_number} answers may contain only A-Z letters, "
                "0-9 numbers, spaces, and periods."
            )
        if len(set(answers)) != len(answers):
            raise ValueError(f"Row {line_number} answers must all be different.")

        questions.append({
            "game": row["game"],
            "question": row["question"],
            "correct_answer": answers[0],
            "wrong_answers": tuple(answers[1:]),
            "difficulty": row["difficulty"],
        })

    return questions


def validate_question_csv(csv_text):
    try:
        questions = parse_question_csv(csv_text)
    except ValueError as error:
        return False, str(error)
    return True, f"CSV is valid: {len(questions)} data row(s)."
