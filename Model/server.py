
from Model import question_set


MAX_SERVER_NAME_LENGTH = 60


def validate_server_name(name):
    server_name = name.strip()
    if not server_name:
        return server_name, "Enter a name for this server."
    if len(server_name) > MAX_SERVER_NAME_LENGTH:
        return server_name, "Server names must be 60 characters or fewer."
    return server_name, None


def next_server_name(existing_names):
    taken = {name.casefold() for name in existing_names}
    server_number = 1
    while f"server {server_number}".casefold() in taken:
        server_number += 1
    return f"Server {server_number}"


def find_due_questions(question_sets, review_cards, now):
    due_questions = []
    seen_questions = set()
    for question_set_id, csv_text in question_sets:
        for question in question_set.parse_question_csv(csv_text):
            question_key = question_set.question_review_key(
                question["question"]
            )
            question_identity = (question_set_id, question_key)
            if question_identity in seen_questions:
                continue
            seen_questions.add(question_identity)
            card = review_cards.get(question_identity)
            due = question_set.get_card_due(card, now) if card else None
            if card is None or due <= now:
                due_questions.append(question_identity)
    return due_questions


def build_server_status(server_id, name, is_default, question_sets, review_cards, now):
    due_questions = find_due_questions(question_sets, review_cards, now)
    question_set_count = len(question_sets)
    return {
        "id": server_id,
        "name": name,
        "is_default": is_default,
        "question_set_count": question_set_count,
        "due_question_count": len(due_questions),
        "online": question_set_count > 0 and not due_questions,
    }
