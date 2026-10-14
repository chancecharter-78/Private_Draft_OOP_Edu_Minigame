"""Compatibility imports for the player data repository.

New application code should depend on focused repository interfaces instead of
this legacy module name.
"""

import psycopg
import streamlit as st

from models.questions import (
    ANSWER_COLUMNS,
    MAX_ANSWER_LENGTH,
    QUESTION_REVIEW_MIGRATION_MESSAGE,
    REQUIRED_COLUMNS,
)
from repositories.database import QuestionReviewSchemaError
from repositories.player_data_repository import (
    PASSWORD_ITERATIONS,
    QUESTION_DATABASE_PATH,
    GameSaveData,
    authenticate_player,
    clean_password,
    clean_username,
    delete_question_set,
    ensure_current_save_data,
    get_leaderboard,
    get_question_set_csv,
    hash_password,
    list_question_sets,
    open_player_database,
    parse_question_csv,
    register_player,
    save_question_set,
    set_active_question_set,
    update_question_set,
    validate_question_csv,
)

__all__ = [
    "ANSWER_COLUMNS",
    "MAX_ANSWER_LENGTH",
    "PASSWORD_ITERATIONS",
    "QUESTION_DATABASE_PATH",
    "QUESTION_REVIEW_MIGRATION_MESSAGE",
    "REQUIRED_COLUMNS",
    "GameSaveData",
    "QuestionReviewSchemaError",
    "authenticate_player",
    "clean_password",
    "clean_username",
    "delete_question_set",
    "ensure_current_save_data",
    "get_leaderboard",
    "get_question_set_csv",
    "hash_password",
    "list_question_sets",
    "open_player_database",
    "parse_question_csv",
    "register_player",
    "save_question_set",
    "set_active_question_set",
    "update_question_set",
    "validate_question_csv",
    "psycopg",
    "st",
]
