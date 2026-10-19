
import csv
import hashlib
import random
from datetime import datetime, timezone
from io import StringIO


REQUIRED_COLUMNS = (
    "game",
    "question",
    "correct answer",
    "wrong answer 1",
    "wrong answer 2",
    "wrong answer 3",
)
ANSWER_COLUMNS = (
    "correct answer",
    "wrong answer 1",
    "wrong answer 2",
    "wrong answer 3",
)
MAX_ANSWER_LENGTH = 32
MAX_SET_NAME_LENGTH = 60
ANSWER_PUNCTUATION = ".,!?+-*/#$@"



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
                not (
                    character.isalnum()
                    or character in f" {ANSWER_PUNCTUATION}"
                )
                for character in answer
            )
            for answer in answers
        ):
            raise ValueError(
                f"Row {line_number} answers may contain only A-Z letters, "
                f"0-9 numbers, spaces, and {ANSWER_PUNCTUATION} punctuation."
            )
        if len(set(answers)) != len(answers):
            raise ValueError(f"Row {line_number} answers must all be different.")

        questions.append({
            "game": row["game"],
            "question": row["question"],
            "correct_answer": answers[0],
            "wrong_answers": tuple(answers[1:]),
        })

    return questions


def validate_question_csv(csv_text):
    try:
        questions = parse_question_csv(csv_text)
    except ValueError as error:
        return False, str(error)
    return True, f"CSV is valid: {len(questions)} data row(s)."


def get_schema():
    return {"required_columns": REQUIRED_COLUMNS, "optional_columns": ()}


def get_csv_template():
    return (
        "game,question,correct answer,wrong answer 1,wrong answer 2,"
        "wrong answer 3\n"
        "Science,Which planet is known as the Red Planet?,MARS,VENUS,"
        "JUPITER,MERCURY\n"
    )


def get_csv_example():
    return [
        {"CSV field": "game", "Example": "Science"},
        {"CSV field": "question", "Example": "Which planet is known as the Red Planet?"},
        {"CSV field": "correct answer", "Example": "MARS"},
        {"CSV field": "wrong answer 1", "Example": "VENUS"},
        {"CSV field": "wrong answer 2", "Example": "JUPITER"},
        {"CSV field": "wrong answer 3", "Example": "MERCURY"},
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
        "- wrong answer 3\n\n"
        "Add one question per row. Include a subject in game, a concise question, "
        "one correct answer, and three different wrong answers. Every answer "
        "must be different and no more than 32 characters, using A-Z letters, "
        f"0-9 numbers, spaces, and {ANSWER_PUNCTUATION} punctuation. Bit Fit "
        "keeps spaces as pre-filled word breaks and has three choices in each "
        "active character column. "
        "Quote any CSV field containing commas, quotation marks, or line breaks. "
        "Do not include markdown fences or text outside the CSV."
    )


def validate_set_name(name):
    if not name:
        return "Enter a name for this question set."
    if len(name) > MAX_SET_NAME_LENGTH:
        return "Question set names must be 60 characters or fewer."
    if not all(char.isalnum() or char in " _-." for char in name):
        return "Use only letters, numbers, spaces, periods, hyphens, or underscores."
    return None



def question_review_key(question_text):
    return hashlib.sha256(question_text.encode("utf-8")).hexdigest()


def get_card_due(card, default_due):
    if not card or not card.get("due"):
        return default_due
    due = datetime.fromisoformat(card["due"])
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    return due.astimezone(timezone.utc)


def build_question_pool(question_set_rows):
    questions = []
    for question_set_id, csv_text in question_set_rows:
        questions.extend(
            {
                **question,
                "_question_set_id": question_set_id,
            }
            for question in parse_question_csv(csv_text)
        )
    return questions


def choose_question(
    questions,
    previous_question,
    review_states,
    now,
    repairing,
    required_reviews,
    seen_reviews,
):
    if previous_question is None:
        previous_questions = set()
    elif isinstance(previous_question, str):
        previous_questions = {previous_question}
    else:
        previous_questions = set(previous_question)
    available = [
        question for question in questions
        if question["question"] not in previous_questions
    ]
    candidates = available or questions
    due_candidates = []
    other_candidates = []
    for question in candidates:
        review_key = (
            question["_question_set_id"],
            question["question"],
        )
        card_key = (
            question["_question_set_id"],
            question_review_key(question["question"]),
        )
        card = review_states.get(card_key)
        due = get_card_due(card, now) if card else None
        question_due_now = card is None or due <= now
        question["_was_due_for_review"] = (
            card_key in required_reviews
            if repairing
            else question_due_now
        )
        question["_server_repair_mode"] = repairing
        if question["_was_due_for_review"] and review_key not in seen_reviews:
            due_candidates.append(question)
        elif review_key not in seen_reviews:
            other_candidates.append(question)

    if due_candidates:
        return random.choice(due_candidates)
    if other_candidates:
        return random.choice(other_candidates)
    return random.choice(candidates)
