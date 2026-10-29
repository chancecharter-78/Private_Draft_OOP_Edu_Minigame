"""Per-game-flow cache of the question pool and review cards.

Every Supabase call opens a brand-new connection, and drawing a question
needs two of them (question sets + review cards).  Neither changes while a
game flow is running (review cards are only saved when the flow ends), so
they are loaded once and reused for every later round.

The cache lives in session state under a non-shared key, so start_game()
wipes it automatically at the start of the next flow.
"""

from datetime import datetime, timezone

import streamlit as st

from Model import question_set
from Repository import question_set_repository, review_repository

CACHE_KEY = "question_context_cache"


def _load_context(player_key, server_id):
    resolved_server_id, rows = question_set_repository.get_server_question_sets(
        player_key,
        server_id,
    )
    questions = question_set.build_question_pool(rows)
    if not questions:
        raise ValueError("This server does not have any question sets selected.")
    review_states = review_repository.get_review_cards(
        player_key,
        resolved_server_id,
    )
    return {
        "player_key": player_key,
        "requested_server_id": server_id,
        "questions": questions,
        "review_states": review_states,
    }


def draw_question(save_data, previous_question=None, server_id=None):
    """Same result as player.get_random_question, minus the repeat DB reads."""
    player_key = save_data.player_name.casefold()
    context = st.session_state.get(CACHE_KEY)
    if (
        context is None
        or context["player_key"] != player_key
        or context["requested_server_id"] != server_id
    ):
        context = _load_context(player_key, server_id)
        st.session_state[CACHE_KEY] = context

    question = question_set.choose_question(
        context["questions"],
        previous_question,
        context["review_states"],
        datetime.now(timezone.utc),
        repairing=st.session_state.get("server_repair_active", False),
        required_reviews=set(
            st.session_state.get("server_repair_due_questions", [])
        ),
        seen_reviews=set(st.session_state.get("server_review_seen", [])),
    )
    return dict(question)
