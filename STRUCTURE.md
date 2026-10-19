# Project structure (MVCR)

`app.py` stays in the project root and is the only entry point:
`streamlit run app.py`.

| Layer | Folder | Rule |
| --- | --- | --- |
| Model | `Model/` | Rules and data shapes. No Streamlit calls, no SQL. |
| View | `View/` | Draws screens. Calls controller functions for every click. |
| Controller | `Controller/` | Callbacks, `st.session_state`, game flow. Calls Model and Repository. |
| Repository | `Repository/` | All database and file access (SQL lives only here). |

Dependencies point one way: View -> Controller -> Model / Repository.
Model never imports anything above it; Repository never imports Model, View or Controller.

## Minigames
- `View/minigame.py`: merged screens for Slider, Bit Fit, Hacking, plus the shared timer, combo, countdown and result table.
- `Controller/minigame.py`: merged controller for the same (timer, combo, game flow, and each game's callbacks).
- `Model/slider.py`, `bit_fit.py`, `hacking.py`: one model per game.
- `Model/combo_system.py`, `game_flow.py`, `timer.py`, `progression_engine.py`, `spaced_repetition.py`: shared rules.

## Other features (one file per feature in each layer)
| Feature | View | Controller | Model | Repository |
| --- | --- | --- | --- | --- |
| Accounts | `account.py` | `account.py` | `account.py` | `player_repository.py` |
| Player / score | `home.py`, `leaderboard.py` | `player.py` | `player.py` | `player_repository.py` |
| Question sets | `question_sets.py` | `question_sets.py` | `question_set.py` | `question_set_repository.py` |
| Servers | `servers.py` | `servers.py` | `server.py` | `server_repository.py` |
| Review cards | (none) | `player.py` | `spaced_repetition.py` | `review_repository.py` |
| Navigation | `navigation.py` | `navigation.py` | (none) | (none) |
| Static pages | `about.py`, `source.py` | (none) | (none) | (none) |

## Where the old files went
| Old file | Now |
| --- | --- |
| `nierva_slider.py` / `nierva_bit_fit.py` / `nierva_hacking.py` | rules -> `Model/`, screens -> `View/minigame.py`, callbacks -> `Controller/minigame.py` |
| `nierva_progression.py` | constants -> `Model/game_flow.py`, flow -> `Controller/minigame.py`, countdown and result screens -> `View/minigame.py` |
| `nierva_timer.py` | `format_time` -> `Model/timer.py`, start/stop -> `Controller/minigame.py`, display -> `View/minigame.py` |
| `nierva_csvdb.py` | `View/question_sets.py`, `Controller/question_sets.py`, `Model/question_set.py` |
| `nierva_save_data.py` | split across all four layers (see the feature table) |
| sign-in, sidebar, page routing in `nierva_app.py` | `View/account.py`, `View/navigation.py`, `Controller/navigation.py` |

`nierva_questions.csv` (the starter questions) stays in the project root.
