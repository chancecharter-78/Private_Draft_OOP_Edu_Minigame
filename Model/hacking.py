
import random


TERMINAL_DUMP_LENGTH = 784
NOISE_CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$#@%&!?+-*/"


def expected_dump_length(words):
    return max(TERMINAL_DUMP_LENGTH, sum(len(word) + 5 for word in words))


def random_noise(length):
    return "".join(random.choice(NOISE_CHARACTERS) for _ in range(length))


def split_noise(text):
    fragments = []
    position = 0
    while position < len(text):
        remaining_length = len(text) - position
        fragment_length = min(remaining_length, random.randint(5, 10))
        tail_length = remaining_length - fragment_length
        if 0 < tail_length < 5:
            fragment_length += tail_length
        fragments.append((text[position:position + fragment_length], False))
        position += fragment_length
    return fragments


def generate_terminal_dump_data(words):
    dump_length = expected_dump_length(words)
    word_count = len(words)
    ordered_words = list(words)
    random.shuffle(ordered_words)

    min_gaps = max(word_count - 1, 0)
    extra = dump_length - sum(len(word) for word in words) - min_gaps
    cuts = sorted(random.randint(0, extra) for _ in range(word_count))
    gaps = [cuts[0]]
    gaps += [1 + cuts[i] - cuts[i - 1] for i in range(1, word_count)]
    gaps.append(extra - cuts[-1])

    segments = []
    for index, word in enumerate(ordered_words):
        segments.extend(split_noise(random_noise(gaps[index])))
        segments.append((word, True))
    segments.extend(split_noise(random_noise(gaps[-1])))

    dump = "".join(text for text, _ in segments)
    return dump, segments


def generate_terminal_dump(words):
    dump, _ = generate_terminal_dump_data(words)
    return dump


def evaluate_guess(guess, password):
    feedback = ["-"] * len(guess)
    remaining = {}

    for letter in password:
        remaining[letter] = remaining.get(letter, 0) + 1

    for index, letter in enumerate(guess):
        if index < len(password) and letter == password[index]:
            feedback[index] = letter
            remaining[letter] -= 1

    for index, letter in enumerate(guess):
        if feedback[index] == "-" and remaining.get(letter, 0) > 0:
            feedback[index] = "/"
            remaining[letter] -= 1

    return "".join(feedback)


def escape_label(text):
    return "".join(f"\\{ch}" if ch in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~" else ch for ch in text)
