
from datetime import datetime, timezone

import streamlit as st

from Model import question_set, server, spaced_repetition
from Model.player import GameSaveData
from Repository import (
    player_repository,
    question_set_repository,
    review_repository,
    server_repository,
)

PLAYER_NOT_ON_LEADERBOARD = "This player is not in the shared leaderboard."


def ensure_current_save_data(save_data=None):
    if save_data is None:
        return GameSaveData()
    if isinstance(save_data, GameSaveData):
        return save_data

    return GameSaveData(
        player_name=getattr(save_data, "player_name", "Player 1"),
        starting_score=getattr(save_data, "_score", 0),
        completed_rounds=getattr(save_data, "_completed_rounds", 0),
        history=getattr(save_data, "_game_history", []),
    )


def get_save_data():
    st.session_state.save_data = ensure_current_save_data(
        st.session_state.get("save_data")
    )
    return st.session_state.save_data


def _key(save_data):
    return save_data.player_name.casefold()


def add_score(save_data, amount):
    if amount <= 0:
        return False
    score = player_repository.add_score(_key(save_data), amount)
    if score is None:
        raise ValueError(PLAYER_NOT_ON_LEADERBOARD)
    save_data.set_totals(score)
    return True


def record_clear(save_data, game_name, level_cleared, details="", points=None):
    if level_cleared <= 0:
        return False
    if points is None:
        points = 100 * level_cleared
    if points < 0:
        return False

    totals = player_repository.insert_clear(
        _key(save_data),
        game_name,
        level_cleared,
        points,
        details,
    )
    if totals is None:
        raise ValueError(PLAYER_NOT_ON_LEADERBOARD)
    score, completed_rounds = totals
    save_data.set_totals(score, completed_rounds)
    save_data.add_history_entry(game_name, level_cleared, points, details)
    return True


def reset_save(save_data):
    if not player_repository.reset_progress(_key(save_data)):
        raise ValueError(PLAYER_NOT_ON_LEADERBOARD)
    save_data.clear_progress()
    return True


def reset_save_data():
    reset_save(st.session_state.save_data)
    st.session_state.save_reset_notice = True


def get_leaderboard(limit=20):
    rows = player_repository.get_leaderboard_rows(limit)
    return [
        {"Player": name, "Score": score, "Clears": clears}
        for name, score, clears in rows
    ]


def get_random_question(save_data, previous_question=None, server_id=None):
    key = _key(save_data)
    server_id, rows = question_set_repository.get_server_question_sets(
        key,
        server_id,
    )
    questions = question_set.build_question_pool(rows)
    if not questions:
        raise ValueError("This server does not have any question sets selected.")

    review_states = review_repository.get_review_cards(key, server_id)
    return question_set.choose_question(
        questions,
        previous_question,
        review_states,
        datetime.now(timezone.utc),
        repairing=st.session_state.get("server_repair_active", False),
        required_reviews=set(
            st.session_state.get("server_repair_due_questions", [])
        ),
        seen_reviews=set(st.session_state.get("server_review_seen", [])),
    )


def record_question_review(
    save_data,
    question_text,
    rating,
    question_set_id=None,
    server_id=None,
):
    return review_repository.update_review_card(
        _key(save_data),
        server_id,
        question_set_id,
        question_set.question_review_key(question_text),
        lambda current_card: spaced_repetition.advance_review_card(
            current_card,
            rating,
        ),
    )


def get_due_question_ids(save_data, server_id):
    question_sets, review_cards = server_repository.fetch_server_review_data(
        _key(save_data),
        server_id,
    )
    return server.find_due_questions(
        question_sets,
        review_cards,
        datetime.now(timezone.utc),
    )
