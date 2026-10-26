
import random
import string

from Model.question_set import ANSWER_PUNCTUATION


CHOICE_CHARACTERS = string.ascii_uppercase + string.digits + "."
PUNCTUATION_CHARACTERS = ANSWER_PUNCTUATION
DEFAULT_COLUMN_COUNT = 10
CHOICES_PER_COLUMN = 3
BIT_FIT_REFRESH_SECONDS = 0.25


def make_reveal_schedules(letter_count):
    early_count = min(random.randint(1, 2), max(0, letter_count - 1))
    early_schedules = []

    for _ in range(early_count):
        dash_start = random.uniform(6, 15)
        hash_start = dash_start + random.uniform(1.5, 2.5)
        letter_time = hash_start + random.uniform(1.5, 2.5)
        early_schedules.append((dash_start, hash_start, letter_time))

    final_reveal = max(
        random.triangular(16, 25, 18),
        max((item[2] for item in early_schedules), default=0) + 1.5,
    )
    later_count = letter_count - early_count
    later_times = []
    if later_count > 1:
        earliest = max((item[2] for item in early_schedules), default=0) + 0.5
        later_times = sorted(
            random.uniform(earliest, final_reveal - 1)
            for _ in range(later_count - 1)
        )
    if later_count:
        later_times.append(final_reveal)

    schedules = list(early_schedules)
    for letter_time in later_times:
        hash_start = letter_time - random.uniform(1.5, 2.5)
        dash_start = hash_start - random.uniform(1.5, 2.5)
        schedules.append((dash_start, hash_start, letter_time))
    return schedules


def create_cipher(answer, round_number):
    cipher_answer = answer
    column_count = max(DEFAULT_COLUMN_COUNT, len(cipher_answer))
    answer_positions = sorted(
        random.sample(range(column_count), len(cipher_answer))
    )
    answer_layout = [None] * column_count
    active_columns = [False] * column_count
    space_columns = [False] * column_count
    options = [None] * column_count
    player_letters = [""] * column_count
    answer_letters = [None] * column_count
    for index, character in zip(answer_positions, cipher_answer):
        answer_layout[index] = character
        if character == " ":
            space_columns[index] = True
            options[index] = []
            continue

        active_columns[index] = True
        answer_letters[index] = character
        if character.isalpha() and character.isascii():
            character_pool = string.ascii_uppercase
        elif character.isdigit() and character.isascii():
            character_pool = string.digits
        elif character in PUNCTUATION_CHARACTERS:
            character_pool = PUNCTUATION_CHARACTERS
        else:
            raise ValueError(
                f"Unsupported answer character for Bit Fit: {character!r}"
            )

        choices = [character]
        choices.extend(
            random.sample(
                [candidate for candidate in character_pool if candidate != character],
                CHOICES_PER_COLUMN - 1,
            )
        )
        random.shuffle(choices)
        options[index] = choices
        player_letters[index] = random.choice([
            candidate for candidate in choices if candidate != character
        ])

    for index in range(column_count):
        if options[index] is None:
            options[index] = random.sample(
                list(CHOICE_CHARACTERS),
                CHOICES_PER_COLUMN,
            )
            player_letters[index] = random.choice(options[index])

    schedules = make_reveal_schedules(sum(active_columns))
    active_indexes = [index for index, active in enumerate(active_columns) if active]
    reveal_stages = [None] * column_count
    for index, schedule in zip(active_indexes, schedules):
        reveal_stages[index] = schedule

    return {
        "cipher_answer": cipher_answer,
        "answer_layout": answer_layout,
        "column_count": column_count,
        "active_columns": active_columns,
        "space_columns": space_columns,
        "options": options,
        "player_letters": player_letters,
        "answer_letters": answer_letters,
        "reveal_stages": reveal_stages,
    }


def get_next_choice(options, player_letters, index):
    choices = options[index]
    current = choices.index(player_letters[index])
    return choices[(current + 1) % len(choices)]


def get_revealed_count(reveal_stages, elapsed):
    return sum(
        1
        for stage in reveal_stages
        if stage is not None and elapsed >= stage[2]
    )


def displayed_hint(elapsed, stage, answer_letter):
    dash_start, hash_start, reveal_time = stage
    if elapsed < dash_start:
        return " "
    if elapsed < hash_start:
        return "-"
    if elapsed < reveal_time:
        return "#"
    return answer_letter


def decode_player_answer(player_letters, active_columns, answer_layout, column_count):
    return "".join(
        player_letters[index]
        if active_columns[index]
        else answer_layout[index] or ""
        for index in range(column_count)
        if answer_layout[index] is not None
    )


def calculate_points(round_number, revealed_count, letter_count):
    if revealed_count == 0:
        return 300 * round_number
    if revealed_count == letter_count:
        return 50 * round_number
    if revealed_count <= 3:
        return 250 * round_number
    return 100 * round_number
