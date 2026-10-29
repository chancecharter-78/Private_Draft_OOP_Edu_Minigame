
import random
import time

import streamlit as st

from Controller import player, question_cache, servers
from Model import (
    bit_fit,
    combo_system,
    game_flow,
    hacking,
    slider,
    spaced_repetition,
    timer,
)


def _draw_question(previous_question):
    return player.get_random_question(
        player.get_save_data(),
        previous_question,
        server_id=st.session_state.get("active_server_id"),
    )



def start_timer(game_key="default"):
    st.session_state[f"{game_key}_start_time"] = time.monotonic()
    st.session_state[f"{game_key}_is_active"] = True
    st.session_state[f"{game_key}_elapsed"] = 0.0


def stop_timer(game_key="default"):
    if st.session_state.get(f"{game_key}_is_active", False):
        elapsed = get_elapsed(game_key)
        st.session_state[f"{game_key}_elapsed"] = elapsed
        st.session_state[f"{game_key}_is_active"] = False
        return elapsed
    return st.session_state.get(f"{game_key}_elapsed", 0.0)


def get_elapsed(game_key="default"):
    if st.session_state.get(f"{game_key}_is_active", False):
        start_time = st.session_state.get(f"{game_key}_start_time", time.monotonic())
        return time.monotonic() - start_time
    return st.session_state.get(f"{game_key}_elapsed", 0.0)


def is_timer_active(game_key="default"):
    return st.session_state.get(f"{game_key}_is_active", False)



def ensure_combo_state():
    st.session_state.setdefault("combo_streak", 0)
    st.session_state.setdefault("combo_multiplier", 1.00)
    return {
        "streak": st.session_state.combo_streak,
        "multiplier": st.session_state.combo_multiplier,
    }


def apply_win(game_name, *, elapsed_seconds, revealed_count=None,
              total_letters=None, correct_questions=None):
    combo = ensure_combo_state()
    streak, multiplier = combo_system.win_state(combo["streak"])

    base_points = combo_system.compute_game_base_score(
        game_name,
        elapsed_seconds=elapsed_seconds,
        revealed_count=revealed_count,
        total_letters=total_letters,
        correct_questions=correct_questions,
    )
    final_points = int(base_points * multiplier)

    st.session_state.combo_streak = streak
    st.session_state.combo_multiplier = multiplier
    st.toast(f"{game_name}: +{final_points} pts ({multiplier:.2f}x combo)")
    return {
        "game": game_name,
        "streak": streak,
        "multiplier": multiplier,
        "base_points": base_points,
        "final_points": final_points,
    }


def apply_soft_fail(game_name):
    combo = ensure_combo_state()
    next_streak, next_multiplier = combo_system.soft_fail_state(
        combo["streak"]
    )

    st.session_state.combo_streak = next_streak
    st.session_state.combo_multiplier = next_multiplier
    st.toast(f"{game_name}: combo slipped to {next_multiplier:.2f}x")
    return {
        "game": game_name,
        "streak": next_streak,
        "multiplier": next_multiplier,
    }


def apply_hard_fail(game_name):
    streak, multiplier = combo_system.hard_fail_state()
    st.session_state.combo_streak = streak
    st.session_state.combo_multiplier = multiplier
    st.toast(f"{game_name}: combo reset to 1.00x")
    return {
        "game": game_name,
        "streak": streak,
        "multiplier": multiplier,
    }



SHARED_SESSION_KEYS = {
    "page",
    "project",
    "game",
    "set",
    "username",
    "save_data",
    "flow_game",
    "flow_clears",
    "flow_target",
    "review_history",
    "game_result_ready",
    "game_next_game",
    "game_start_started_at",
    "game_start_active",
    "review_user_rating",
    "review_saved",
    "active_server_id",
    "server_repair_active",
    "server_repair_due_questions",
    "repair_sequence_toast_shown",
    "server_repair_notice",
}


def start_game(game_name):
    if game_name not in game_flow.GAME_ORDER:
        return

    for key in list(st.session_state.keys()):
        if key not in SHARED_SESSION_KEYS:
            del st.session_state[key]

    st.session_state.page = game_name
    st.session_state.set = game_name
    st.session_state.project = True
    st.session_state.game = True
    st.session_state.flow_game = game_name
    st.session_state.flow_clears = 0
    st.session_state.flow_target = random.randint(
        *game_flow.GAME_CLEAR_RANGES[game_name]
    )
    st.session_state.review_history = []
    st.session_state.game_result_ready = False
    st.session_state.game_next_game = None
    st.session_state.game_start_started_at = None
    st.session_state.game_start_active = False
    st.session_state.review_user_rating = 3
    st.session_state.review_saved = False
    st.session_state.server_review_seen = []
    st.session_state.game_flow_succeeded = False


def start_server_game(server_id, repairing):
    save_data = st.session_state.save_data
    st.session_state.active_server_id = server_id
    st.session_state.server_repair_active = repairing
    st.session_state.repair_sequence_toast_shown = False
    st.session_state.server_repair_due_questions = (
        player.get_due_question_ids(save_data, server_id)
        if repairing
        else []
    )
    game_name = random.choice(game_flow.GAME_ORDER)
    start_game(game_name)


def reset_game(game_name):
    start_game(game_name)


def advance_start_gate(timer_key):
    if st.session_state.get("game_start_active", False):
        return "active", None, False

    announce_repair = False
    started_at = st.session_state.get("game_start_started_at")
    if started_at is None:
        started_at = time.monotonic()
        st.session_state.game_start_started_at = started_at
        if (
            st.session_state.get("server_repair_active", False)
            and not st.session_state.get("repair_sequence_toast_shown", False)
        ):
            announce_repair = True
            st.session_state.repair_sequence_toast_shown = True
    elapsed = time.monotonic() - started_at
    phase, countdown = game_flow.get_start_phase(elapsed)
    if phase == "ready":
        st.session_state.game_start_active = True
        start_timer(timer_key)
    return phase, countdown, announce_repair


def record_question_result(
    question,
    chosen_answer,
    won,
    elapsed_seconds,
    target_seconds,
    score=None,
):
    automated_rating = spaced_repetition.map_performance_to_rating(
        won,
        elapsed_seconds,
        target_seconds,
        score=score,
    )
    st.session_state.setdefault("review_history", []).append({
        "question": question["question"],
        "question_set_id": question.get("_question_set_id"),
        "review_required": question.get("_was_due_for_review", False),
        "repair_mode": question.get("_server_repair_mode", False),
        "chosen_answer": chosen_answer,
        "correct_answer": question["correct_answer"],
        "won": won,
        "elapsed_seconds": elapsed_seconds,
        "automated_rating": automated_rating,
    })
    if question.get("_question_set_id") is not None:
        seen = st.session_state.setdefault("server_review_seen", [])
        question_identity = (
            question["_question_set_id"],
            question["question"],
        )
        if question_identity not in seen:
            seen.append(question_identity)
    return automated_rating


def finish_game(game_name, message, flow_succeeded=True):
    next_games = [name for name in game_flow.GAME_ORDER if name != game_name]
    st.session_state.game_result_ready = True
    st.session_state.game_next_game = random.choice(next_games)
    st.session_state.game_result_message = message
    st.session_state.game_start_active = False
    st.session_state.game_flow_succeeded = flow_succeeded


def record_failure(game_name, message=""):
    st.session_state.flow_game = game_name
    st.session_state.flow_clears = 0
    st.session_state.flow_target = random.randint(
        *game_flow.GAME_CLEAR_RANGES[game_name]
    )
    finish_game(game_name, message, flow_succeeded=False)


def record_success(game_name, success_message=""):
    if st.session_state.get("flow_game") != game_name:
        start_game(game_name)

    st.session_state.flow_clears += 1
    if st.session_state.flow_clears < st.session_state.flow_target:
        return False

    finish_game(game_name, success_message)
    return True


def build_result_rows():
    rows = []
    for result in st.session_state.get("review_history", []):
        final_rating = spaced_repetition.combine_ratings(
            result["automated_rating"],
            st.session_state.get("review_user_rating", 3),
        )
        rows.append({
            "Question": result["question"],
            "Your answer": result["chosen_answer"],
            "Correct answer": result["correct_answer"],
            "Time (s)": round(result["elapsed_seconds"], 1),
            "Automatic": game_flow.RATING_LABELS[result["automated_rating"]],
            "Final": game_flow.RATING_LABELS[final_rating],
        })
    return rows


def save_rating_and_continue(game_name, save_data):
    user_rating = st.session_state.review_user_rating
    for result in st.session_state.get("review_history", []):
        if (
            st.session_state.get("server_repair_active", False)
            and not result["review_required"]
        ):
            continue
        final_rating = spaced_repetition.combine_ratings(
            result["automated_rating"],
            user_rating,
        )
        player.record_question_review(
            save_data,
            result["question"],
            final_rating,
            question_set_id=result["question_set_id"],
            server_id=st.session_state.get("active_server_id"),
        )
    if st.session_state.get("server_repair_active", False):
        st.session_state.server_repair_due_questions = (
            player.get_due_question_ids(
                save_data,
                st.session_state.active_server_id,
            )
        )
    if (
        st.session_state.get("server_repair_active", False)
        and st.session_state.get("game_flow_succeeded", False)
    ):
        server = servers.get_server_status(
            save_data.player_name,
            st.session_state.active_server_id,
        )
        if server["due_question_count"] == 0 and server["question_set_count"] > 0:
            st.session_state.server_repair_active = False
            st.session_state.server_repair_due_questions = []
            st.session_state.repair_sequence_toast_shown = False
            st.session_state.server_repair_notice = (
                f"{server['name']} is back online."
            )
            st.session_state.page = "Servers"
            st.session_state.game = False
            st.session_state.project = False
            return
    continue_to_next_game(game_name)


def continue_to_next_game(game_name):
    next_game = st.session_state.get("game_next_game")
    if next_game not in game_flow.GAME_ORDER:
        next_game = random.choice(
            [name for name in game_flow.GAME_ORDER if name != game_name]
        )
    start_game(next_game)



SLIDER_STATE_KEYS = (
    "slider_level",
    "slider_wins",
    "slider_history",
    "slider_total_elapsed",
    "slider_position",
    "slider_direction",
    "slider_over",
    "slider_msg",
    "slider_last_update",
    "slider_pending_initial_start",
    "slider_position_history",
    "slider_question",
    "slider_choices",
    "slider_correct_index",
    "slider_round_locked",
)


def reset_slider_timer():
    start_timer("slider")
    st.session_state.slider_last_update = time.monotonic()
    st.session_state.slider_over = False


def slider_state_initialized():
    return all(key in st.session_state for key in SLIDER_STATE_KEYS)


def init_slider():
    st.session_state.slider_level = 1
    st.session_state.slider_wins = 0
    st.session_state.slider_history = []
    st.session_state.slider_total_elapsed = 0.0
    st.session_state.slider_position = 50
    st.session_state.slider_direction = 1
    st.session_state.slider_over = False
    st.session_state.slider_msg = ""
    st.session_state.slider_last_update = time.monotonic()
    st.session_state.slider_pending_initial_start = True
    st.session_state.slider_position_history = []
    st.session_state.slider_round_locked = False
    set_slider_question()


def ensure_slider_ready():
    if not slider_state_initialized():
        init_slider()


def consume_slider_pending_start():
    if st.session_state.get("slider_pending_initial_start", False):
        st.session_state.slider_last_update = time.monotonic()
        st.session_state.slider_pending_initial_start = False


def set_slider_question():
    previous_question = st.session_state.get("slider_question", {}).get("question")
    question = _draw_question(previous_question)
    choices, correct_index = slider.shuffle_choices(question)

    st.session_state.slider_question = question
    st.session_state.slider_choices = choices
    st.session_state.slider_correct_index = correct_index
    st.session_state.slider_position_history = []


def update_marker():
    history = st.session_state.setdefault("slider_position_history", [])
    now = time.monotonic()
    previous_update = st.session_state.get("slider_last_update", now)
    elapsed = now - previous_update
    st.session_state.slider_last_update = now

    if st.session_state.get("slider_over", True):
        return

    speed = slider.speed_for_level(st.session_state.slider_level)
    position, direction = slider.advance_position(
        st.session_state.slider_position,
        st.session_state.slider_direction,
        speed,
        elapsed,
    )
    st.session_state.slider_position = position
    st.session_state.slider_direction = direction
    history.append((position, direction))
    st.session_state.slider_position_history = history[-3:]


def end_slider():
    total_sliders = slider.TOTAL_SLIDERS
    minimum_wins = slider.MINIMUM_WINS
    elapsed = st.session_state.slider_total_elapsed
    if st.session_state.slider_wins >= minimum_wins:
        message = (
            f"🎉 Repair Success! {st.session_state.slider_wins} of {total_sliders} sliders successfully cleared in {timer.format_time(elapsed)}!"
        )
        st.session_state.slider_over = True
        st.session_state.slider_completed_summary = {
            "won": True,
            "message": message,
            "history": list(st.session_state.slider_history),
            "score": player.get_save_data().check_score(),
            "timer": timer.format_time(elapsed),
        }
        finish_game("Slider", message)
        return

    st.session_state.slider_over = True
    st.session_state.slider_msg = (
        f"❌ Repair Failed... {st.session_state.slider_wins} of {total_sliders} cleared."
        f"You needed {minimum_wins} to continue. "
        f"Game over after {timer.format_time(elapsed)}."
    )
    st.session_state.slider_completed_summary = {
        "won": False,
        "message": st.session_state.slider_msg,
        "history": list(st.session_state.slider_history),
        "score": player.get_save_data().check_score(),
        "timer": timer.format_time(elapsed),
    }
    record_failure("Slider", st.session_state.slider_msg)


def slider_finish_round(won, selected_index=None):
    level = st.session_state.slider_level
    question = st.session_state.slider_question
    choices = st.session_state.slider_choices
    position = st.session_state.slider_position
    elapsed = get_elapsed("slider")
    stop_timer("slider")
    st.session_state.slider_total_elapsed += elapsed
    if selected_index is None:
        selected_index = slider.zone_index_for_position(position)
    selected_answer = choices[selected_index]
    correct_answer = question["correct_answer"]
    automated_rating = record_question_result(
        question,
        selected_answer,
        won,
        elapsed,
        game_flow.QUESTION_TARGET_SECONDS["Slider"],
    )
    st.session_state.slider_history.append({
        "level": level,
        "question": question["question"],
        "choices": choices,
        "position": position,
        "won": won,
        "selected_answer": selected_answer,
        "correct_answer": correct_answer,
        "selected_index": selected_index,
        "correct_index": st.session_state.slider_correct_index,
        "elapsed_seconds": elapsed,
        "automated_rating": automated_rating,
    })

    if won:
        answer = choices[st.session_state.slider_correct_index]
        reward = apply_win(
            "Slider",
            elapsed_seconds=elapsed,
            correct_questions=st.session_state.slider_wins + 1,
        )
        player.record_clear(
            player.get_save_data(),
            "Slider Minigame",
            level,
            f"Answered {answer} at {position:.1f}%",
            points=reward["final_points"],
        )
        st.session_state.slider_wins += 1
        st.session_state.slider_msg = f"✅ Correct! Level {level} cleared."
    else:
        apply_soft_fail("Slider")
        st.session_state.slider_msg = (
            f"❌ Incorrect choice. The answer was {question['correct_answer']}."
        )

    if level >= slider.TOTAL_SLIDERS:
        end_slider()
        return

    st.session_state.slider_level += 1
    st.session_state.slider_position = 50
    st.session_state.slider_direction = 1
    set_slider_question()
    st.session_state.slider_round_locked = False
    reset_slider_timer()


def lock_slider():
    if (
        st.session_state.slider_over
        or st.session_state.get("slider_round_locked", False)
    ):
        return
    st.session_state.slider_round_locked = True
    history = st.session_state.get("slider_position_history", [])
    latest_tick = slider.get_stop_position(history)
    if latest_tick is not None:
        position, direction = latest_tick
        st.session_state.slider_position = position
        st.session_state.slider_direction = direction
    selected_index = slider.zone_index_for_position(
        st.session_state.slider_position
    )
    correct_index = st.session_state.slider_correct_index
    tick_grace = slider.tick_grace_from_history(history)
    within_grace = slider.is_position_within_correct_zone(
        st.session_state.slider_position,
        correct_index,
        tick_grace,
    )
    if selected_index == correct_index:
        slider_finish_round(True)
    elif within_grace:
        slider_finish_round(True, selected_index=correct_index)
    else:
        slider_finish_round(False)


def restart_slider():
    start_game("Slider")



def bit_fit_setup_round():
    previous_question = st.session_state.get("bf_question", {}).get("question")
    question = _draw_question(previous_question)
    answer = question["correct_answer"]
    cipher = bit_fit.create_cipher(answer, st.session_state.bf_round)

    st.session_state.bf_question = question
    st.session_state.bf_answer = answer
    st.session_state.bf_cipher_answer = cipher["cipher_answer"]
    st.session_state.bf_answer_layout = cipher["answer_layout"]
    st.session_state.bf_cols = cipher["column_count"]
    st.session_state.bf_active = cipher["active_columns"]
    st.session_state.bf_space_columns = cipher["space_columns"]
    st.session_state.bf_options = cipher["options"]
    st.session_state.bf_player = cipher["player_letters"]
    st.session_state.bf_answer_letters = cipher["answer_letters"]
    st.session_state.bf_answer_reveal_stages = cipher["reveal_stages"]
    st.session_state.bf_reveal_started = time.monotonic()
    st.session_state.bf_msg = ""


def init_bit_fit():
    st.session_state.bf_round = 1
    st.session_state.bf_over = False
    st.session_state.bf_pending_initial_reveal = True
    bit_fit_setup_round()


def ensure_bit_fit_ready():
    if (
        "bf_round" not in st.session_state
        or "bf_options" not in st.session_state
        or "bf_space_columns" not in st.session_state
        or "bf_answer_layout" not in st.session_state
    ):
        init_bit_fit()


def bit_fit_reveal_elapsed():
    return time.monotonic() - st.session_state.bf_reveal_started


def consume_bit_fit_pending_reveal():
    if st.session_state.get("bf_pending_initial_reveal", False):
        st.session_state.bf_reveal_started = time.monotonic()
        st.session_state.bf_pending_initial_reveal = False


def cycle_letter(index):
    if st.session_state.bf_over or not st.session_state.bf_active[index]:
        return
    st.session_state.bf_player[index] = bit_fit.get_next_choice(
        st.session_state.bf_options,
        st.session_state.bf_player,
        index,
    )


def bit_fit_lose_round(message):
    st.session_state.bf_over = True
    st.session_state.bf_msg = message
    stop_timer("bit_fit")
    apply_soft_fail("Bit Fit")
    record_failure("Bit Fit", message)


def submit_round():
    if st.session_state.bf_over:
        return

    active_indexes = [
        index for index, active in enumerate(st.session_state.bf_active) if active
    ]
    answer = bit_fit.decode_player_answer(
        st.session_state.bf_player,
        st.session_state.bf_active,
        st.session_state.bf_answer_layout,
        st.session_state.bf_cols,
    )
    target_seconds = game_flow.QUESTION_TARGET_SECONDS["Bit Fit"]
    if answer != st.session_state.bf_cipher_answer:
        elapsed = stop_timer("bit_fit")
        record_question_result(
            st.session_state.bf_question,
            answer,
            False,
            elapsed,
            target_seconds,
        )
        bit_fit_lose_round(
            f"❌ The letters decoded to {answer or '(empty)'}, not "
            f"{st.session_state.bf_answer}. Failed in {timer.format_time(elapsed)}."
        )
        return

    elapsed = stop_timer("bit_fit")
    record_question_result(
        st.session_state.bf_question,
        answer,
        True,
        elapsed,
        target_seconds,
    )
    revealed_count = bit_fit.get_revealed_count(
        st.session_state.bf_answer_reveal_stages,
        bit_fit_reveal_elapsed(),
    )
    reward = apply_win(
        "Bit Fit",
        elapsed_seconds=elapsed,
        revealed_count=revealed_count,
        total_letters=len(active_indexes),
    )
    points = reward["final_points"]

    player.record_clear(
        player.get_save_data(),
        "Bit Fit",
        st.session_state.bf_round,
        f"Decoded {answer} with {revealed_count} revealed letter(s)",
        points=points,
    )

    success_message = f"🎉 Correct! Round {st.session_state.bf_round} cleared."
    if record_success("Bit Fit", success_message):
        return

    st.session_state.bf_round += 1
    bit_fit_setup_round()
    start_timer("bit_fit")
    st.session_state.bf_msg = f"🎉 Correct! Round {st.session_state.bf_round} started."


def restart_bit_fit():
    start_game("Bit Fit")



def hacking_regenerate_terminal(words):
    (
        st.session_state.hack_terminal_dump,
        st.session_state.hack_terminal_segments,
    ) = hacking.generate_terminal_dump_data(words)
    st.session_state.hack_round = st.session_state.get("hack_round", 0) + 1


def hacking_ensure_terminal_segments():
    segments = st.session_state.get("hack_terminal_segments")
    dump = st.session_state.get("hack_terminal_dump", "")
    valid = (
        isinstance(segments, list)
        and segments
        and isinstance(segments[0], tuple)
        and len(dump) == hacking.expected_dump_length(
            st.session_state.hack_words
        )
    )
    if not valid:
        hacking_regenerate_terminal(st.session_state.hack_words)


def init_hacking():
    previous_questions = st.session_state.get("hack_seen_questions", [])
    question = question_cache.draw_question(
        player.get_save_data(),
        previous_questions,
        server_id=st.session_state.get("active_server_id"),
    )
    previous_questions.append(question["question"])
    st.session_state.hack_seen_questions = previous_questions

    words = [question["correct_answer"], *question["wrong_answers"]]
    random.shuffle(words)

    st.session_state.hack_question = question
    st.session_state.hack_password = question["correct_answer"]
    st.session_state.hack_words = words
    hacking_regenerate_terminal(words)
    st.session_state.hack_attempts = len(words) - 1
    st.session_state.hack_log = []
    st.session_state.hack_input = ""
    st.session_state.hack_over = False
    st.session_state.hack_win = False
    st.session_state.hack_notice = ""
    st.session_state.hack_notice_kind = "info"


def prepare_hacking():
    if "hack_password" not in st.session_state:
        init_hacking()
    hacking_ensure_terminal_segments()


def restart_hacking():
    seen_questions = st.session_state.get("hack_seen_questions", [])
    reset_game("Hacking")
    st.session_state.hack_seen_questions = seen_questions


def hacking_lose_round(message):
    st.session_state.hack_over = True
    st.session_state.hack_win = False
    st.session_state.hack_notice = message
    st.session_state.hack_notice_kind = "error"
    elapsed = stop_timer("hacking")
    chosen_answer = st.session_state.hack_log[-1][0] if st.session_state.hack_log else ""
    record_question_result(
        st.session_state.hack_question,
        chosen_answer,
        False,
        elapsed,
        game_flow.QUESTION_TARGET_SECONDS["Hacking"],
    )
    record_failure("Hacking", message)


def hacking_spend_attempt():
    st.session_state.hack_attempts -= 1
    if st.session_state.hack_attempts <= 0:
        apply_hard_fail("Hacking")
        hacking_lose_round(
            f"💀 Lockout Triggered! Sequence was {st.session_state.hack_password}."
        )
        return True
    apply_soft_fail("Hacking")
    return False


def pick_word(guess=None):
    if st.session_state.hack_over:
        return

    if guess is None:
        guess = st.session_state.get("hack_input", "")
    guess = guess.strip().upper()
    st.session_state.hack_input = ""
    st.session_state.hack_notice_kind = "info"

    if not guess:
        st.session_state.hack_notice = "Enter a word from the terminal dump."
        return
    if guess not in st.session_state.hack_words:
        st.session_state.hack_notice = "Choose one of the words hidden in the terminal dump."
        return
    if any(previous_guess == guess for previous_guess, _ in st.session_state.hack_log):
        st.session_state.hack_notice = "You have already tried that word."
        return

    feedback = hacking.evaluate_guess(guess, st.session_state.hack_password)
    st.session_state.hack_log.append((guess, feedback))
    st.session_state.hack_notice = ""

    if guess != st.session_state.hack_password:
        hacking_spend_attempt()
        return

    st.session_state.hack_win = True
    st.session_state.hack_over = True
    elapsed = stop_timer("hacking")
    base_points = combo_system.compute_game_base_score(
        "Hacking",
        elapsed_seconds=elapsed,
    )
    record_question_result(
        st.session_state.hack_question,
        guess,
        True,
        elapsed,
        game_flow.QUESTION_TARGET_SECONDS["Hacking"],
        score=base_points,
    )
    reward = apply_win("Hacking", elapsed_seconds=elapsed)
    message = (
        f"🎉 Decryption Complete in {timer.format_time(elapsed)}! "
        f"Target sequence was {st.session_state.hack_password}."
    )
    player.record_clear(
        player.get_save_data(),
        "Terminal Hacking",
        1,
        f"Password decrypted in {timer.format_time(elapsed)}",
        points=reward["final_points"],
    )
    if record_success("Hacking", message):
        return

    init_hacking()
    start_timer("hacking")
    st.session_state.hack_notice = message
    st.session_state.hack_notice_kind = "success"


def pick_noise(fragment):
    if st.session_state.hack_over:
        return

    st.session_state.hack_log.append((fragment, "NO MATCH"))
    st.session_state.hack_notice = "Noise selected. One attempt used."
    st.session_state.hack_notice_kind = "info"
    hacking_spend_attempt()


def on_terminal_pick():
    round_id = st.session_state.get("hack_round", 0)
    key = f"hack_pills_{round_id}"
    index = st.session_state.get(key)
    if index is None:
        return
    st.session_state[key] = None
    segments = st.session_state.hack_terminal_segments
    if not 0 <= index < len(segments):
        return
    text, is_word = segments[index]
    (pick_word if is_word else pick_noise)(text)
