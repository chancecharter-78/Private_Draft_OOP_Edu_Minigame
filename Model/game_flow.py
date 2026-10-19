
GAME_ORDER = ("Slider", "Bit Fit", "Hacking")
GAME_CLEAR_RANGES = {
    "Slider": (2, 6),
    "Bit Fit": (5, 8),
    "Hacking": (4, 6),
}
START_DELAY_SECONDS = 3
COUNTDOWN_SECONDS = 3
RATING_LABELS = {
    1: "Again",
    2: "Hard",
    3: "Good",
    4: "Easy",
}
RESULT_COLUMN_WIDTHS = {
    "Question": 260,
    "Your answer": 100,
    "Correct answer": 100,
    "Time (s)": 40,
    "Automatic": 50,
    "Final": 50,
}
QUESTION_TARGET_SECONDS = {
    "Slider": 8.0,
    "Bit Fit": 10.0,
    "Hacking": 8.0,
}


def get_start_phase(elapsed):
    if elapsed < START_DELAY_SECONDS:
        return "delay", None
    countdown_elapsed = elapsed - START_DELAY_SECONDS
    if countdown_elapsed < COUNTDOWN_SECONDS:
        return "countdown", COUNTDOWN_SECONDS - int(countdown_elapsed)
    return "ready", None
