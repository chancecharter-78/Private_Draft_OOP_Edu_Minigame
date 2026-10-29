# Voiding Boredom (Alpha)

A web-based educational game that turns your own question sets into short minigames and schedules reviews with the Free Spaced Repetition Scheduler (FSRS). Built with Python and Streamlit for the IT102 Object-Oriented Programming course.

## The problem

Flashcard review works for long-term retention, but its plain input-output interface is boring, so learners abandon it. Voiding Boredom makes the game itself the review interface: how you perform in the minigames decides which questions come back and when.

**Intended users:** students who want to review their own material (any subject) using spaced repetition.

## Features

- **Custom question sets** – upload CSV files (validated on upload) with one correct answer and three wrong answers per question.
- **Three minigames**
  - **Slider** – stop a bouncing marker in the zone of the correct answer (2–6 rounds of 5 sliders; 3 wins needed per round).
  - **Bit Fit** – assemble the answer from per-column character choices while a hint row slowly reveals letters; answer within five seconds after the final letter appears (5–8 rounds).
  - **Terminal Hacking** – find the correct word hidden in a block of noise; wrong guesses return per-letter feedback (4–6 rounds).
- **Servers** – group question sets into servers. A server is **Idle** (no sets), **Online** (nothing due) or **Offline** (questions due). Repair an offline server by answering its due questions.
- **FSRS scheduling** – each answer becomes a 4-level rating (Again/Hard/Good/Easy) from correctness and speed, capped by the player's own self-rating.
- **Scoring** – speed-based base score, combo multiplier (up to ×1.35), and a rank system.
- **Logic-programming rules** – combo tiers, due-question checks, server status and rating rules are written as facts and rules and answered by a built-in logic engine (`Model/logic_engine.py`, `Model/logic_rules.py`).
- **Accounts and leaderboard** – PBKDF2-HMAC-SHA256 password hashing (random 16-byte salt, 310,000 iterations), persistent scores, global leaderboard.

## OOP implementation and architecture

The project follows an **MVCR** layout (Model, View, Controller, Repository). Dependencies point one way only:

```
View -> Controller -> Model
                   -> Repository -> PostgreSQL
```

| Layer | Folder | Responsibility |
| --- | --- | --- |
| Model | `Model/` | Game rules and data shapes: no Streamlit calls, no SQL |
| View | `View/` | Draws Streamlit screens; calls controller functions |
| Controller | `Controller/` | Session state, callbacks, game flow |
| Repository | `Repository/` | All database access |

OOP concepts used:

- **Abstraction** – `Minigame` (`Model/minigames.py`) is an abstract base class (`abc.ABC`). It declares the abstract methods `start_round()` and `base_score()` that every minigame must provide, so `Minigame` itself cannot be instantiated.
- **Inheritance** – `Slider`, `BitFit` and `Hacking` extend `Minigame` and reuse its shared behavior (`name`, `target_seconds`, `clear_range`, `rate()`). The custom exceptions `DuplicateNameError` and `QuestionReviewSchemaError` (`Repository/database.py`) extend `Exception` and `RuntimeError`.
- **Polymorphism** – each subclass implements `start_round()` and `base_score()` differently (a shuffled choice list, a Bit Fit cipher, a Hacking terminal dump), but all are used through the same `Minigame` interface, looked up with `get_minigame(name)`.
- **Encapsulation** – `Minigame` keeps its name private (`_name`) and exposes it as a read-only property. `GameSaveData` (`Model/player.py`) keeps score, completed rounds and history private, exposes them through methods, and returns copies of its history.
- **Custom engine classes** – `KnowledgeBase`, `Var`, `Term` and `Clause` (`Model/logic_engine.py`) implement a small Prolog-style logic engine (facts, rules, unification, backtracking, arithmetic, negation as failure). `Model/logic_rules.py` holds the game rules (combo tiers, due questions, server online status, performance rating) as a logic program, and the Model functions use it with an automatic fallback to equivalent Python code.
- **Layered architecture** – each layer only knows the layer below it.

See `figures/` for the architecture, class, logic engine, database, server-state and session-flow diagrams.

## Project structure

`app.py` stays in the project root and is the only entry point: `streamlit run app.py`.

Dependencies point one way: View -> Controller -> Model / Repository. Model never imports anything above it; Repository never imports Model, View or Controller.

### Minigames

- `View/minigame.py`: merged screens for Slider, Bit Fit and Hacking, plus the shared timer, combo, countdown and result table.
- `Controller/minigame.py`: merged controller for the same (timer, combo, game flow, and each game's callbacks).
- `Model/slider.py`, `bit_fit.py`, `hacking.py`: one model per game.
- `Model/combo_system.py`, `game_flow.py`, `timer.py`, `progression_engine.py`, `spaced_repetition.py`: shared rules.
- `Model/minigames.py`: abstract `Minigame` class with `Slider`, `BitFit` and `Hacking` subclasses wrapping the functions above.
- `Model/logic_engine.py`, `logic_rules.py`: small Prolog-style logic engine and the game rules written as logic facts and rules (Python fallback if unavailable).
- `tests/`: unit tests for the Model layer. `figures/`: architecture, class, database and flow diagrams. `docs/`: paper additions.

### Other features (one file per feature in each layer)

| Feature | View | Controller | Model | Repository |
| --- | --- | --- | --- | --- |
| Accounts | `account.py` | `account.py` | `account.py` | `player_repository.py` |
| Player / score | `home.py`, `leaderboard.py` | `player.py` | `player.py` | `player_repository.py` |
| Question sets | `question_sets.py` | `question_sets.py` | `question_set.py` | `question_set_repository.py` |
| Servers | `servers.py` | `servers.py` | `server.py` | `server_repository.py` |
| Review cards | (none) | `player.py` | `spaced_repetition.py` | `review_repository.py` |
| Navigation | `navigation.py` | `navigation.py` | (none) | (none) |
| Static pages | `about.py`, `source.py` | (none) | (none) | (none) |

### Where the old files went

| Old file | Now |
| --- | --- |
| `nierva_slider.py` / `nierva_bit_fit.py` / `nierva_hacking.py` | rules -> `Model/`, screens -> `View/minigame.py`, callbacks -> `Controller/minigame.py` |
| `nierva_progression.py` | constants -> `Model/game_flow.py`, flow -> `Controller/minigame.py`, countdown and result screens -> `View/minigame.py` |
| `nierva_timer.py` | `format_time` -> `Model/timer.py`, start/stop -> `Controller/minigame.py`, display -> `View/minigame.py` |
| `nierva_csvdb.py` | `View/question_sets.py`, `Controller/question_sets.py`, `Model/question_set.py` |
| `nierva_save_data.py` | split across all four layers (see the feature table) |
| sign-in, sidebar, page routing in `nierva_app.py` | `View/account.py`, `View/navigation.py`, `Controller/navigation.py` |

`nierva_questions.csv` (the starter questions) stays in the project root.

## Question set format

| Column | Meaning |
| --- | --- |
| `game` | Subject label |
| `question` | The question text |
| `correct answer` | The single correct answer |
| `wrong answer 1` – `wrong answer 3` | Three distinct wrong answers |

Answers: up to 32 characters, using A–Z, 0–9, spaces and `.,!?+-*/#$@` only, and all four must differ. See `nierva_questions.csv` for an example.

## Dependencies

| Package | Purpose |
| --- | --- |
| `streamlit` | Web UI |
| `psycopg[binary]` | PostgreSQL driver |
| `fsrs` | Free Spaced Repetition Scheduler |

## Setup and run locally

Requires Python 3.10 or newer.

```bash
git clone https://github.com/chancecharter-78/Private_Draft_OOP_Edu_Minigame.git
cd Private_Draft_OOP_Edu_Minigame
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Create the database (next section), then provide the connection string as a secret. For local runs create `.streamlit/secrets.toml` (listed in `.gitignore`, never commit it):

```toml
SUPABASE_DB_URL = "postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require"
```

or set the `SUPABASE_DB_URL` environment variable. Then run:

```bash
streamlit run app.py
```

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

## Database setup (Supabase)

The app stores accounts, scores, completed rounds, question sets, servers and review cards directly in Supabase PostgreSQL. It does not use a local SQLite database. The database URL is a server secret: never put it in browser code, commit it, or expose it to users.

1. Create a Supabase project and keep its database password private.
2. For a new, empty database only, open the Supabase SQL Editor and run [`supabase/migrations/20261011000000_create_game_tables.sql`](./supabase/migrations/20261011000000_create_game_tables.sql) once. It creates the core tables and indexes. Do not run it again against a database that already contains app data.
3. Run the review-card migration: [`supabase/migrations/20261014000000_create_question_review_cards.sql`](./supabase/migrations/20261014000000_create_question_review_cards.sql). It adds a table for per-player, per-question-set scheduling state.
4. Run the server migration: [`supabase/migrations/20261018000000_create_servers.sql`](./supabase/migrations/20261018000000_create_servers.sql). It creates three servers for existing accounts, connects each default server to that account's active question set, and moves existing review cards to that default server. For a database that already has the core and review-card tables, run only this new migration.
5. In the project's **Connect** dialog, copy a PostgreSQL connection URI and make sure it includes `sslmode=require`.

New accounts and game progress are written straight to this database. The app does not run migrations automatically.

## Deploy on Streamlit Community Cloud

Open the deployed app's menu, choose **Settings → Secrets**, and add the URI as a TOML string:

```toml
SUPABASE_DB_URL = "postgresql://..."
```

Save the secret and reboot the app. The app reads it from `st.secrets`; never put the URI in source code, commit it, or paste it into chat. App restarts reconnect to the same Supabase database instead of relying on the app's local filesystem.

If a game reports that a required database table is missing, first verify that `SUPABASE_DB_URL` points to the project containing the existing app data, then apply the pending migrations from steps 3 and 4 as applicable. Do not rerun the initial schema setup on a database containing data.

## Install on a persistent Linux host

Use this only if hosting Streamlit on your own persistent Linux server. Copy the repository to `/opt/nierva-game` on a Linux server with Python 3.10 or newer, then run:

```sh
sudo useradd --system --home-dir /opt/nierva-game --shell /usr/sbin/nologin nierva
sudo chown -R nierva:nierva /opt/nierva-game
sudo -u nierva python3 -m venv /opt/nierva-game/.venv
sudo -u nierva /opt/nierva-game/.venv/bin/pip install -r /opt/nierva-game/requirements.txt
```

Create `/etc/nierva-game.env` with the server-side connection string:

```sh
sudo install -m 600 -o root -g root /dev/null /etc/nierva-game.env
sudoedit /etc/nierva-game.env
```

Put this line in the file, using the URI from Supabase:

```text
SUPABASE_DB_URL=postgresql://...
```

Install and start the service:

```sh
sudo install -m 644 /opt/nierva-game/deploy/nierva-app.service /etc/systemd/system/nierva-app.service
sudo systemctl daemon-reload
sudo systemctl enable --now nierva-app
sudo systemctl status nierva-app
```

The service listens only on `127.0.0.1:8501`. Put it behind a TLS-enabled reverse proxy (for example, Nginx or Caddy) before making it reachable on the internet. Review firewall rules so the database and Streamlit port are not publicly exposed, and use the protected environment file instead of typing the connection URI into shell history.

## Tests

`tests/test_model.py` contains 107 unit tests for the Model layer, including checks that the logic rules give the same answers as the plain Python rules. Results are in `tests/test_results.txt`.

## Acknowledgment

Portions of the software were developed with the assistance of GitHub Copilot.
