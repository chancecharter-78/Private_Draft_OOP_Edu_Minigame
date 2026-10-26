
import random


TOTAL_SLIDERS = 5
MINIMUM_WINS = TOTAL_SLIDERS // 2 + 1
SLIDER_REFRESH_SECONDS = 0.2
ZONE_WIDTH = 25
ZONE_COUNT = 4


def speed_for_level(level):
    return 2 + level * 2


def advance_position(position, direction, speed, elapsed):
    phase = position if direction > 0 else 200 - position
    phase = (phase + speed * 10 * elapsed) % 200
    if phase < 100:
        return phase, 1
    return 200 - phase, -1


def get_stop_position(history):
    if not history:
        return None
    return history[-1]


def zone_index_for_position(position):
    return min(int(position // ZONE_WIDTH), ZONE_COUNT - 1)


def is_position_within_correct_zone(position, correct_index, tick_grace):
    zone_start = correct_index * ZONE_WIDTH
    zone_end = (correct_index + 1) * ZONE_WIDTH
    return (
        max(0, zone_start - tick_grace)
        <= position
        <= min(100, zone_end + tick_grace)
    )


def tick_grace_from_history(history):
    if len(history) > 1:
        return abs(history[-1][0] - history[-2][0])
    return 0


def shuffle_choices(question):
    choices = [question["correct_answer"], *question["wrong_answers"]]
    random.shuffle(choices)
    return choices, choices.index(question["correct_answer"])
