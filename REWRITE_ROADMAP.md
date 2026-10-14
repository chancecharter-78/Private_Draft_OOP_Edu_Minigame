# Voiding Boredom: Progressive MVC + Repository Rewrite Roadmap

## Purpose and working method

This roadmap describes a from-scratch rebuild of the current educational
minigame application as it exists in this repository, using Model-View-
Controller (MVC) with Repository as an explicit persistence extension. Follow
it in order. Each stage adds a visible interface surface and then the
controller/model/repository mechanics that make that surface work before
moving on. Do not begin by implementing a large backend disconnected from a
runnable app.

Treat the current app as a behavioral reference, not as a design that must be
copied line-for-line. Rebuild the intended behavior with clearer boundaries,
typed domain data, explicit state transitions, and tests. Keep the existing
app runnable until a replacement vertical slice is verified.

## Target architecture: MVC + Repository

Use the following dependency direction. UI code requests work from a
controller; the controller coordinates domain models and repositories; a
repository owns persistence details. The Model must not import Streamlit or
execute SQL. The View must not issue SQL or calculate business decisions.

```text
app.py (composition root)
  └── controllers/ (routes, callbacks, use-case orchestration)
        ├── models/ (domain records, validation, game rules, state transitions)
        ├── repositories/ (interfaces and PostgreSQL implementations)
        └── views/ (Streamlit rendering and widget events)

Allowed dependency direction:
  app -> controllers -> models
                    -> repositories -> database driver
  app/controllers -> views (rendering calls)
  views -> controller actions (callbacks / submitted input)

Forbidden dependencies:
  models -> Streamlit, repositories, or SQL
  views -> repositories, database driver, or score/review rules
  repositories -> Streamlit widgets or page rendering
```

### Directory layout to build incrementally

```text
.
├── app.py
├── controllers/
│   ├── __init__.py
│   ├── application_controller.py
│   ├── authentication_controller.py
│   ├── question_set_controller.py
│   ├── game_flow_controller.py
│   ├── slider_controller.py
│   ├── bit_fit_controller.py
│   └── hacking_controller.py
├── models/
│   ├── __init__.py
│   ├── account.py
│   ├── question.py
│   ├── question_set.py
│   ├── game_session.py
│   ├── game_result.py
│   ├── progression.py
│   ├── scoring.py
│   └── review.py
├── repositories/
│   ├── __init__.py
│   ├── database.py
│   ├── player_repository.py
│   ├── question_set_repository.py
│   ├── game_result_repository.py
│   └── review_repository.py
├── views/
│   ├── __init__.py
│   ├── application_view.py
│   ├── authentication_view.py
│   ├── home_view.py
│   ├── question_sets_view.py
│   ├── leaderboard_view.py
│   └── games/
│       ├── __init__.py
│       ├── slider_view.py
│       ├── bit_fit_view.py
│       └── hacking_view.py
├── supabase/migrations/
└── tests/
```

Keep timer presentation under the View and timer rules/state under the Model.
Keep FSRS scheduling calculations under the Model and their storage under the
Review Repository. Keep the app's composition root (`app.py`) responsible for
constructing repositories/controllers and injecting dependencies; it should
not contain page logic or SQL.

### Responsibility rules

- **Model:** Represents domain facts and pure behavior: account/question
  records, CSV validation rules, game state transitions, movement, feedback,
  score/rank calculations, and review scheduling. A Model function should be
  testable without launching Streamlit or opening a database connection.
- **View:** Renders Streamlit elements and translates user interaction into
  controller calls. It may own transient widget values, but it does not decide
  whether an answer earns points or issue SQL.
- **Controller:** Handles a use case. It reads submitted input, asks Models to
  validate/calculate, invokes Repository methods to load/save, and returns a
  view-ready result or explicit error state. It coordinates state transitions
  but should not embed database SQL or detailed Streamlit layout.
- **Repository:** Defines how domain data is loaded and persisted. It owns
  parameterized SQL, row-to-model conversion, transaction boundaries,
  ownership filters, connection use, and persistence errors. It does not
  render UI or contain game scoring rules.
- **Composition root:** Constructs concrete PostgreSQL repositories, injects
  them into controllers, and starts the app. Tests can construct controllers
  with in-memory/fake repositories instead.
- **Compatibility adapters:** During migration, the existing root-level
  `nierva_*.py` modules may remain as thin import shims. They must not become a
  second implementation. Remove them only after all callers and tests use the
  MVC packages.

### Current modules mapped to their eventual MVC homes

| Existing source | Destination responsibility |
|---|---|
| `nierva_app.py` | Split into `app.py`, `controllers/application_controller.py`, `controllers/authentication_controller.py`, `views/application_view.py`, and `views/authentication_view.py` |
| `nierva_save_data.py` | Split CSV/domain validation into `models/`; move account, question-set, score, leaderboard, and review SQL into focused `repositories/`; expose use cases through `controllers/` |
| `nierva_csvdb.py` | Move rendering to `views/question_sets_view.py`; move upload/editor/save orchestration to `controllers/question_set_controller.py` |
| `nierva_progression.py` | Split flow transitions/rating orchestration into `controllers/game_flow_controller.py`, pure state/rating rules into `models/`, and result rendering into `views/` |
| `nierva_timer.py` | Split monotonic timer state/calculation into `models/`; keep the live Streamlit timer display in shared UI/view code |
| `nierva_combo_system.py` | Move pure combo and scoring rules to `models/scoring.py`; let game controllers persist the returned score receipt through a repository |
| `nierva_progression_engine.py` | Move to `models/progression.py` |
| `nierva_spaced_repetition.py` | Move rating and scheduling calculations to `models/review.py`; move persisted card reads/writes to `repositories/review_repository.py` |
| `nierva_slider.py` | Split into `views/games/slider_view.py`, `controllers/slider_controller.py`, and pure movement/result rules in `models/` |
| `nierva_bit_fit.py` | Split into `views/games/bit_fit_view.py`, `controllers/bit_fit_controller.py`, and pure cipher/reveal rules in `models/` |
| `nierva_hacking.py` | Split into `views/games/hacking_view.py`, `controllers/hacking_controller.py`, and pure dump/feedback/attempt rules in `models/` |
| `nierva_home.py` | Move rendering to `views/home_view.py`; obtain rank and leaderboard view models through a controller |
| `nierva_leaderboard.py` | Move rendering to `views/leaderboard_view.py`; query through a controller backed by `player_repository.py` |
| `nierva_about.py`, `nierva_source.py` | Move static page rendering under `views/` |
| SQL migrations | Keep under `supabase/migrations/`; repositories rely on schema but never apply migrations during a normal request |
| `test_nierva_program.py` | Split into unit tests for Models, repository contract/integration tests, controller use-case tests, and UI/browser tests |

### Migration rule

Do not move files in one mass rename. For each vertical slice, extract a
Model, then a Repository contract/implementation if data is involved, wire a
Controller, add a View, and test that slice. Keep the old app executable as a
reference. When the full MVC app passes behavior and data-preservation checks,
switch the deployment entry point to `app.py`; retain thin compatibility
shims only if external scripts or tests still import the old module names.

### Current implementation status

The repository is in a **partial compatibility migration**, not yet a complete
MVC cutover:

- `models/` now contains the pure question CSV rules, scoring rules, review
  scheduling rules, and rank progression functions.
- `repositories/database.py` owns database URL resolution and connection
  creation. `repositories/player_data_repository.py` contains the current
  PostgreSQL-backed player/question-set/save operations.
- `controllers/application_controller.py` owns page dispatch;
  `controllers/combo_controller.py` coordinates combo state and scoring model
  calls.
- `views/` contains the static pages, homepage, leaderboard, and question-set
  editor.
- The old `nierva_*.py` import paths remain as compatibility adapters where
  moved modules have callers/tests that still use the old names.
- Game screens and callbacks, authentication UI, review/result rendering,
  and several cross-game transitions still need to be separated into their
  dedicated Controllers and Views. The current deployed entry point remains
  `nierva_app.py`; do not switch deployment to `app.py` until those slices
  have been migrated and verified.

For every stage:

1. Write the smallest useful tests for the pure logic before or alongside the
   implementation.
2. Put business rules in Models, persistence in Repositories, orchestration in
   Controllers, and rendering in Views.
3. Run the app and exercise the interface that was just built.
4. Check the changed behavior against the acceptance points in this roadmap.
5. Do not proceed while the stage is knowingly broken.
6. Keep credentials out of source control and never point development tests at
   production data.

## Existing application map

The current app is a single-process Streamlit application. Its entry point is
`nierva_app.py`; it selects one page from a route map and stores much of its
temporary state in `st.session_state`.

| Current file | Current responsibility to understand before replacing |
|---|---|
| `nierva_app.py` | Streamlit startup, login/register screen, sidebar navigation, page dispatch, top-level database error messages |
| `nierva_save_data.py` | CSV parsing, Supabase PostgreSQL access, account functions, question-set ownership, scores, game-clear history, review-card persistence |
| `nierva_csvdb.py` | Question-set browser, active-set selection, CSV upload/editor/validation/save/delete UI |
| `nierva_progression.py` | Game sequence, random clear targets, start delay/countdown, result and review screens, game-flow state |
| `nierva_timer.py` | Monotonic timers, elapsed-time formatting, updating timer display |
| `nierva_combo_system.py` | Combo tiers, win/failure transitions, and per-game base-score calculation |
| `nierva_progression_engine.py` | Rank thresholds and lifetime-score-to-rank conversion |
| `nierva_spaced_repetition.py` | Performance ratings, conservative combined rating, FSRS card scheduling |
| `nierva_slider.py` | Moving marker game, stop callback, five-round outcome and wins |
| `nierva_bit_fit.py` | Character-column cipher game, reveal schedule, cycling and decode |
| `nierva_hacking.py` | Terminal dump, valid-word guesses, duplicate-letter feedback and attempts |
| `nierva_home.py` | Player score/rank overview, reset action, leaderboard preview |
| `nierva_leaderboard.py` | Shared leaderboard display |
| `nierva_about.py`, `nierva_source.py` | Static information pages |
| `supabase/migrations/*.sql` | Core PostgreSQL tables and additive review-card table |
| `test_nierva_program.py` | Unit tests and a SQLite-backed adapter used to exercise PostgreSQL-facing code without production data |
| `DEPLOYMENT.md`, `deploy/nierva-app.service`, `.env.example` | Database configuration and hosting guidance |

Current important behavior includes:

- Registration and login use a normalized username key and PBKDF2 password
  hashing. Usernames and passwords have explicit length and character limits.
- Each account owns question sets. A set contains raw CSV and can be active,
  edited, downloaded, or deleted if it is not active.
- CSV questions have a game/subject, prompt, one correct answer, three
  distinct wrong answers, and difficulty. Answers are uppercased and limited
  to ASCII letters, digits, spaces, and periods; each answer is at most 32
  characters.
- Game questions are selected from the active set, avoid the immediately
  previous question where possible, and are influenced by due review cards.
- A game flow begins with a three-second preparation delay and a three-second
  countdown. The flow then cycles between Slider, Bit Fit, and Hacking until
  that game's random clear target is reached; completing/failing a game shows
  results and requires an explicit Continue.
- Slider has five levels and requires at least three wins. The marker reflects
  elapsed monotonic time and moves across four equal answer zones. Its current
  stop rule uses the latest recorded sample, with a one-refresh-sample movement
  margin on either side of the correct zone.
- Bit Fit removes spaces from the answer, uses one column per character, has a
  default of ten columns and expands for longer answers. Active columns have
  choices matching the answer character type (letters, digits, or punctuation
  for a period). It reveals answer characters over time and has a preview of
  the next option beneath each cycling button.
- Hacking hides the correct answer among words in a generated terminal dump.
  It has one fewer attempt than candidate words and gives positional feedback:
  exact characters are shown, present-but-misplaced characters use `#`, and
  absent characters use `-`. Correct answers advance to another round unless
  the overall game clear target is met.
- Points are calculated by game-specific time/reveal/win-count tiers, then
  multiplied by a combo tier. Lifetime score is also the XP total used to
  derive Adventure Rank; the rank-up cost starts at 1,500 and increases by
  250 for each rank.
- At a game-flow result, automated performance ratings can be combined with a
  user rating. The more conservative of the two ratings is stored through FSRS
  against the question and question-set identity.
- Core schema setup is for a new empty database. Existing databases must be
  preserved; apply only additive migrations that are actually missing.

## Sequential rebuild

### Phase 1 — Boot, identity, and navigation

#### [ ] 1. Create the smallest runnable application shell

**Deep Blueprint**

- Decide the new package layout before adding domain behavior. A practical
  starting structure is an entry point plus separate `domain`, `application`,
  `infrastructure`, and `ui` modules. Keep this structure small until the
  application demonstrates a real need for more files.
- Create the entry point that configures the page once, initializes a session
  state object, and renders a shell with a title and an empty content region.
- Give the session an explicit starting route such as `login`; do not use
  implicit missing-key errors as a routing mechanism.
- Add a single page dispatcher that receives a route value and calls exactly
  one page renderer. Unknown route values should render a visible safe fallback
  and a way back to a known route.
- Add a smoke test proving the entry point imports and the default route is
  selected without connecting to Supabase.
- Run the app locally and verify a browser receives a rendered page before
  adding the login or game screens.

#### [ ] 2. Build the login/register gateway interface

**Deep Blueprint**

- Render a clear title, short explanation, and a login form with username and
  password fields. Keep the password field masked.
- Render a separate registration view with username, password, and explicit
  password-length guidance. Provide one control to switch between the two
  views.
- Keep the form values separate from authenticated identity. A typed form
  submission should produce an authentication request; it must not directly
  set the logged-in player.
- Represent visible form status explicitly: idle, submitting, validation
  error, authentication error, or successful transition.
- Disable the submit action while a request is in progress to reduce duplicate
  submissions.
- Verify keyboard submission, empty values, error visibility, and switching
  between forms in a browser.

#### [ ] 3. Implement authentication and account persistence

**Deep Blueprint**

- Define the player identity fields: display username, case-folded username
  key, salt, password hash, cumulative score, completed-round count, and active
  question-set reference.
- Normalize usernames once in a domain/application boundary. Preserve the
  display spelling separately from the uniqueness key.
- Validate username and password before reaching the repository. Preserve the
  current username limit (20), permitted letters/numbers/space/hyphen/
  underscore, and password bounds (8–128) unless you intentionally decide to
  revise and test them.
- Hash passwords with a per-account cryptographically random salt and a
  password-specific key-derivation function; compare derived values using a
  constant-time comparison. Never store or log plaintext passwords.
- Create a database connection factory that reads a server-side
  `SUPABASE_DB_URL` from environment or Streamlit secrets. Raise a clear
  configuration error when neither is set. Do not store a live connection in
  user session state.
- Make account creation atomic: insert player, insert starter question set,
  then set it active in one transaction. A duplicate username is a normal,
  visible validation result; unrelated database failures must remain explicit.
- On login, return an authenticated player object only after the password
  matches. Do not reveal whether a failed login was caused by an unknown
  username or incorrect password.
- Test successful and failed login, duplicate registration, normalization,
  password limits, random salts, and transaction rollback using a test
  database adapter.

**Architectural divergence point — authentication boundary**

- **Option A: Functions called directly by page callbacks.** Keep validation,
  password hashing, SQL, and session mutation in a few functions, similar to
  the current app. This is quickest initially but makes transaction behavior
  and UI error handling difficult to test in isolation.
- **Option B: Authentication service plus repository.** Let the UI call an
  application service; the service validates and hashes, and a repository
  performs SQL. This creates a little more structure but gives clean unit
  test seams and limits accidental coupling to Streamlit.
- **Option C: External identity provider.** Delegate password storage and
  sessions to a provider while retaining an application player profile in
  PostgreSQL. This is a larger migration and introduces provider configuration
  and availability concerns.
- **Ripple Effect:** Option B is the smoothest fit if this remains a small
  Streamlit app that is expected to grow: it isolates UI reruns from
  transactions without forcing a full web-service architecture. Option A
  can be adequate for a prototype but tends to grow into callback code that
  mixes state, security, and SQL. Option C reduces custom credential logic
  but adds a service dependency and account-linking work.

#### [ ] 4. Build the authenticated application frame and navigation UI

**Deep Blueprint**

- Once the session contains an authenticated player, replace the login
  gateway with the app shell and navigation controls.
- Display a stable player identity label and routes for Homepage, Minigames,
  Question Sets, Leaderboard, About, and Source.
- Render game selection only while a game flow is active, and keep information
  pages distinct from game pages.
- Add a sign-out control that clears authentication and game-only state but
  does not change server-side data.
- Keep navigation callbacks focused on changing a route/requesting a flow
  transition; page renderers should not each reimplement the sidebar.
- Verify every route works after login, after refresh, and after sign-out.

#### [ ] 5. Implement route transitions and session-state ownership

**Deep Blueprint**

- Define a session model with separate sections for authentication, route,
  game-flow state, active game state, notices, and view-only widget values.
- Document which state survives a page change and which state is reset when a
  new game starts. Never use a broad “delete every unknown key” loop as the
  long-term ownership model.
- Implement route transitions for: open Homepage, enter Minigames, select a
  game, navigate to an information page, return to Homepage, sign out, and
  resume an active game.
- Give every multi-step callback a single owner and make repeated callback
  execution safe where a rerun may repeat it.
- Keep Streamlit widget-owned keys distinct from derived/business state.
  Update widget-owned values before widget construction or through callbacks.
- Add tests for route changes, state reset boundaries, repeat submission, and
  identity preservation.

**Architectural divergence point — UI/session state**

- **Option A: Streamlit session state is the application state.** Store game
  fields and transitions directly in `st.session_state`. This is easy to
  prototype but makes state transitions depend on Streamlit rerun order.
- **Option B: Typed application state mirrored into Streamlit.** Define
  dataclasses/enums for domain state and treat Streamlit state as a
  serialization/adapter boundary. This improves validation and testability
  while remaining compatible with Streamlit.
- **Option C: Server-side session store with opaque browser session id.**
  Keep authoritative state outside Streamlit memory. This helps distributed
  workers and long-lived sessions but requires expiry, synchronization, and
  operational infrastructure.
- **Ripple Effect:** Option B usually provides the best balance here: game
  code can be tested without driving the UI, while the current single-process
  deployment avoids the complexity of Option C. Option A is fastest only while
  the game state remains very small; the timer fragments, callbacks, result
  flow, and widget keys already make rerun-sensitive state a correctness risk.

### Phase 2 — Question data and the first complete game-flow shell

#### [ ] 6. Build the question-set browser interface

**Deep Blueprint**

- Render the authenticated player's saved sets, clearly identify the active
  set, and show how many questions each set contains.
- Provide an active-set selector, download action, and an editor with
  separate upload and paste/edit modes.
- The editor needs a set target, set name, CSV text, validation message, save
  action, and delete action for inactive sets. The active set must not be
  deletable.
- On selecting another saved set, load that set's exact CSV and name into the
  editor. On loading an upload, treat it as a new set until explicitly saved.
- Show preview and validation feedback before save; never imply persistence
  succeeded until the repository confirms it.
- Verify selecting/editing one set cannot silently overwrite another set.

#### [ ] 7. Implement CSV parsing and question validation

**Deep Blueprint**

- Build a pure parser that accepts CSV text and returns a structured list of
  question records or a precise validation error.
- Require the columns `game`, `question`, `correct answer`, `wrong answer 1`,
  `wrong answer 2`, `wrong answer 3`, and `difficulty`. Normalize headers
  case-insensitively and trim surrounding whitespace; reject blank or
  duplicate headers and missing required headers.
- Parse with a real CSV parser so quoted commas, quotes, and line breaks are
  handled correctly. Reject malformed quoting and rows with a different field
  count than the header.
- Trim every field; reject missing required values. Uppercase answer fields;
  require ASCII A–Z, digits, spaces, and periods only; cap each answer at 32
  characters; require the four answers in a row to be distinct.
- Return records with a stable shape, for example `game`, `question`,
  `correct_answer`, `wrong_answers`, and `difficulty`.
- Preserve the input CSV text for exact download/editing, while using parsed
  records for play. Do not regenerate stored CSV from normalized records
  unless that behavior is consciously chosen.
- Test valid files, BOM/UTF-8 behavior, quoted fields, empty rows, bad counts,
  duplicate answers, invalid characters, and length boundaries.

#### [ ] 8. Implement editor interactions: upload, preview, and safe save

**Deep Blueprint**

- Decode uploaded files explicitly as UTF-8 with optional BOM; show a useful
  error for undecodable input rather than silently dropping bytes.
- Store editor draft fields independently from the active question-set widget
  value. A widget key should not also act as an implicit save target.
- Make target changes load a matching name/CSV draft together. Track the
  loaded target identity and refuse save if the selected target changes before
  the corresponding draft is loaded.
- Validate continuously or on demand, but keep validation pure and do not
  write to the database during validation.
- Save an existing set through an update path; save an upload/new draft through
  an insert path. Show transaction-confirmed success and preserve the draft on
  validation/database failure.
- Add tests for a renamed set, new upload set, changed target, and duplicate
  set name. Confirm the database write and displayed editor selection agree.

#### [ ] 9. Persist question sets with owner isolation and safe migrations

**Deep Blueprint**

- Define repository operations for list, read, insert, update, activate, and
  delete question sets. Every read/write must include the authenticated
  owner key in its authorization predicate.
- Preserve case-insensitive per-owner name uniqueness and use parameterized
  SQL for all values.
- Enforce owner references and active-set validity in the database schema as
  well as the application layer where practical.
- Design the core schema for a new empty database and additive migrations for
  later changes. Keep migration execution separate from normal app startup.
- Preserve existing player/question-set/score data during upgrades. Never
  rerun the initial schema setup on a populated database.
- Use a disposable test database or adapter for tests; never truncate or
  migrate production as part of a test.
- Verify set A cannot list, download, activate, modify, or delete set B's data
  even when a foreign set id is submitted.

**Architectural divergence point — question-set representation**

- **Option A: Store raw CSV only.** Reparse when reading questions. This
  preserves imports exactly and keeps schema simple, but every game selection
  reparses the file and validation is repeated.
- **Option B: Store raw CSV plus normalized question rows.** Preserve the
  original import while indexing parsed questions. This speeds queries and
  supports per-question foreign keys, but requires atomic synchronization on
  every edit and a migration path.
- **Option C: Store structured question rows only.** Use normalized tables as
  the canonical record and generate CSV only when exporting. This supports
  richer queries but risks changing formatting and raises import/export
  compatibility work.
- **Ripple Effect:** Option A is simplest while sets are small and the entire
  active CSV can be parsed in memory. Option B becomes attractive if question
  sets grow or database filtering becomes important. Option C is strongest
  for a mature question-authoring product, but is likely unnecessary cost for
  the current CSV-centric workflow.

#### [ ] 10. Build the Minigames entry screen and game-start UI

**Deep Blueprint**

- Add a Minigames gateway that selects the first game (currently Slider by
  default) or resumes a chosen game flow.
- Render the selected game title and an explicit start preparation screen.
- Show the three-second “Get ready” delay followed by the visible 3, 2, 1
  countdown. Do not start the gameplay timer during the initial delay.
- Make the start transition happen exactly once: when the countdown finishes,
  mark game start active, start its timer, and render the active game.
- Provide navigation to Homepage and allow game selection when the flow
  supports it.
- Test the phase function at boundary times (before 3 seconds, exactly 3,
  intermediate countdown, exactly 6) without sleeping in tests.

#### [ ] 11. Implement the cross-game flow state machine

**Deep Blueprint**

- Define game identifiers and their display order: Slider, Bit Fit, Hacking.
- Define the current per-game clear-target ranges: Slider 2–6, Bit Fit 5–8,
  Hacking 4–6. Pick a target once when a game flow begins; do not reroll it on
  every rerun.
- Track current game, clears in that game, target clears, active countdown,
  game result readiness, selected next game, and review history.
- On each successful round, increment that game's clear count exactly once.
  If it is below target, remain in the game; at target, freeze gameplay and
  show results.
- On failure, end the current game and show its failure summary. Do not count a
  failure as a clear.
- After Continue or Save Rating and Continue, begin a different game, reset
  game-local state, and initialize a new clear target. Do not auto-transition
  before the user sees the result.
- Make transitions idempotent against duplicate button callbacks.
- Test success-to-next-round, target completion, failure, explicit Continue,
  and selecting a different game.

**Architectural divergence point — game implementation structure**

- **Option A: Independent page modules.** Keep one UI module per minigame and
  share a few helpers. This fits the current three distinct mechanics and is
  easy to navigate, but shared flow behavior can drift.
- **Option B: Game adapter/protocol.** Each game implements common lifecycle
  operations such as initialize, render, submit, and summarize. The flow
  orchestrator stays generic, but the abstraction must allow genuinely
  different controls.
- **Option C: Data-driven generic game engine.** Represent each game as
  configurable rules and generic components. This can reduce repeated code
  for similar quiz games but can obscure unique mechanics such as real-time
  motion and cipher reveals.
- **Ripple Effect:** Option A with a small explicit shared flow service is a
  low-risk starting point. Option B is valuable if new minigames are likely;
  keep the protocol narrow and test each adapter independently. Option C may
  be efficient for multiple-choice variants but can make the current Slider
  feel less responsive and make game-specific bugs hard to isolate.

### Phase 3 — Shared mechanics and score display

#### [ ] 12. Build the shared question and round-status interface

**Deep Blueprint**

- For an active question, display the prompt, subject/game, and difficulty in
  the same order across all three games.
- Show round/level, saved score, and combo status without each game inventing
  a different label or state lookup.
- Display validation errors, incorrect-answer notices, success notices, and
  terminal-game results as distinct message types.
- Ensure the question stays stable for the duration of its round, including
  during timer/fragment refreshes.
- Avoid reusing input widget keys between rounds; key each input by game and
  round identity or reset it before constructing the next widget.
- Verify notices remain understandable after the question changes or a new
  round begins.

#### [ ] 13. Implement question selection and review-aware scheduling

**Deep Blueprint**

- Build a question-selection service taking player identity, active question
  set, prior question(s), and current time; return one parsed question and its
  stable identity.
- Prefer questions whose review cards are due. If all eligible questions are
  scheduled in the future, choose the earliest due candidate; if a question
  set has no due metadata, use a documented fallback such as random selection.
- Avoid repeating the immediately previous question where another candidate
  exists. Define behavior when the set has only one question.
- Keep random choice injectable or seedable for tests; do not make scheduling
  tests flaky.
- Associate a review identity with the owning user, set id, and stable question
  identity. If using question text as identity, define how edits to prompt
  text affect its review history.
- Test due vs future cards, ties, only-one-question sets, previous-question
  exclusion, empty sets, and replacement of a deleted/edited set.

#### [ ] 14. Build the shared timer display

**Deep Blueprint**

- Show elapsed time in a consistent `MM:SS.t` format in each game.
- Update only the timer region at the required refresh interval; do not rerun
  unrelated editor/game content every tenth of a second.
- Show a stable stopped value after win/failure and a fresh zero value on a
  new timed round.
- Test time formatting for zero, tenths rounding, minute boundaries, and
  negative values.
- Confirm on a browser that the display refreshes while game state remains
  stable.

#### [ ] 15. Implement timer lifecycle and monotonic elapsed-time mechanics

**Deep Blueprint**

- Use a monotonic clock for elapsed durations; wall-clock time can change and
  must not determine game timing.
- Define explicit timer state (`started_at`, `elapsed`, `active`) and
  operations `start`, `read_elapsed`, and `stop`.
- Starting resets elapsed state; stopping freezes the current elapsed value
  and can be repeated safely without adding more time.
- Give each game/round a distinct timer identity or pass timer state as an
  explicit object. Never allow one game timer to accidentally overwrite
  another.
- Test the timer with a fake clock rather than real delays.
- Verify button callbacks and fragment reruns agree on the same timer state.

#### [ ] 16. Build combo and points display; implement scoring mechanics

**Deep Blueprint**

- Show current combo multiplier and win streak in the shared status area.
- Define win multiplier tiers: streak 0–2 => 1.00x, 3–5 => 1.05x, 6–8 =>
  1.15x, 9–11 => 1.25x, 12+ => 1.35x.
- Define a pure base-points function with explicit game input data:
  - Bit Fit uses elapsed seconds and number of revealed answer characters:
    current tiers are 500, 300, 200, or 100 base points.
  - Hacking uses elapsed seconds: current tiers are 500 below 5 seconds, 300
    below 7, 200 below 9, and 100 otherwise.
  - Slider uses elapsed time and correct-question count. Preserve current tier
    boundaries deliberately rather than copying accidental overlapping
    conditions.
- On a win, compute base points, advance the streak, derive the multiplier,
  calculate integer final points, and return a receipt containing all
  components. Persist exactly that final amount.
- On a soft failure, decay combo by 0.10x without going below 1.00x; on a hard
  failure, reset streak and multiplier to baseline.
- Make base points and multiplier functions pure so tests cover every
  threshold and boundary (`<` versus `<=`) without a Streamlit session.
- Decide whether the game score thresholds shown here are the intended
  design. Current score rules have changed over time, so use a product tuning
  table and tests as the source of truth after the rewrite begins.

**Architectural divergence point — score rules**

- **Option A: Hard-code rules in a shared function.** Keep a game-name branch
  and return points. This is compact for three games but grows into branching
  logic as mechanics expand.
- **Option B: Typed per-game scoring policies.** Give each game a policy that
  receives a result record and returns base points. The combo service applies
  multipliers consistently. This keeps game scoring distinct and easy to test.
- **Option C: Store tunable scoring tables in configuration/database.** This
  lets designers tune without code releases but requires validation,
  versioning, and safeguards against a bad live configuration.
- **Ripple Effect:** Option B is a good balance for this game set: it prevents
  one game's new input from contaminating another game's scoring signature.
  Option A is simpler while rules remain stable. Option C can improve tuning
  cadence but should not be introduced until there is a real need for live
  changes and a safe rollout path.

#### [ ] 17. Build the Homepage progress overview

**Deep Blueprint**

- Display player name, cumulative score, Adventure Rank, and completed clears.
- Render a rank progress bar and text showing current remainder XP over the
  XP requirement for the next rank.
- Display the shared leaderboard preview.
- Provide an explicit save-reset action with confirmation, then render a clear
  success/failure notice. Reset must not delete the player account or other
  users' data.
- Keep the view read-only except for intentional actions; derive displayed
  rank progress from saved cumulative score.
- Test zero score, exact rank boundary, overflow across multiple ranks, and
  reset permissions.

#### [ ] 18. Implement Adventure Rank progression and score persistence

**Deep Blueprint**

- Preserve lifetime score as the durable source of truth. Rank starts at 1;
  rank 1 to 2 requires 1,500 XP; each later requirement increases by 250 XP.
- Convert total XP to rank plus remainder by repeatedly subtracting each
  threshold. Carry all overflow and do not reset the cumulative score at rank
  up.
- Treat score as XP for display, but keep the domain naming clear so lifetime
  leaderboard score and current-rank remainder are not confused.
- Validate score additions as non-negative and persist per-clear score plus
  clear history in one database transaction.
- Load total score and completed clears from the persisted player record.
  Recompute rank from total score instead of storing a separately drifting
  rank counter.
- Test exact thresholds (1,499/1,500), rank 10, multiple-level overflow,
  non-negative inputs, and old accounts with existing totals.

### Phase 4 — Game vertical slices: interface then mechanics

#### [ ] 19. Build the Slider interface shell

**Deep Blueprint**

- Render the current question, game metadata, level out of five, timer, four
  answer zones, marker, and a Stop button.
- Render the four choices in a responsive single row and keep the marker
  visually aligned to four equal-width zones across the full 0–100% range.
- Keep Stop outside any rapidly refreshing timer/animation fragment so it
  remains stable, visible, and clickable.
- Disable or lock Stop after the first callback while processing the round.
- Display per-round success/failure text and a completed-game result state
  without rendering an active control underneath it.
- Verify layout and button behavior at desktop and narrow viewport widths.

#### [ ] 20. Implement Slider motion, stop tolerance, and five-round outcome

**Deep Blueprint**

- Initialize level 1, zero wins, empty history, position 50%, direction right,
  and a fresh question with four shuffled answer choices. Store the correct
  choice index once per round.
- Advance position from elapsed monotonic time, not the number of browser
  refreshes. Current speed is `2 + level * 2`; reflect direction at the 0 and
  100 boundaries rather than allowing an unbounded marker.
- Maintain a bounded recent-position history for the refresh-tick stop
  calculation. On Stop, lock the round, use the newest recorded point, and
  allow a one-tick movement margin on either side of the correct zone.
- Map zones consistently: four intervals of 25 percentage points. Define
  the exact boundary convention so 25, 50, 75, and 100 never select two zones.
- If grace accepts a point just outside the target zone, record the selected
  answer as the correct option but preserve the actual marker position in the
  history/receipt.
- On each stop, freeze elapsed time, record question result/rating, apply win
  or soft-fail combo, persist points for wins, then either initialize the next
  level or finish after five levels.
- Require at least three wins to clear. Otherwise record failure and show the
  result screen. Prevent duplicate stop callbacks from duplicating score,
  history, or question-review entries.
- Test movement under multiple refresh schedules for equal elapsed time,
  endpoint reflection, exact zone edges, one-tick grace on both sides,
  duplicate stop, all-win completion, and fewer-than-three-wins failure.

**Architectural divergence point — real-time marker rendering**

- **Option A: Streamlit fragment with periodic updates.** Calculate marker
  position from elapsed time during each fragment rerun. This uses current
  infrastructure and keeps state on the server, but smoothness is limited by
  rerun/network latency.
- **Option B: Browser-side animation component.** Animate via JavaScript and
  submit a timestamp/position only when Stop is clicked. This can feel much
  smoother but requires a custom component and careful server/client
  synchronization.
- **Option C: Discrete manual ticks.** Move the marker in fixed visible steps
  controlled by user actions. This is highly deterministic but changes the
  game's feel and pacing.
- **Ripple Effect:** Option A is the lowest-effort path for the current app;
  elapsed-time-based motion prevents speed changing with refresh count.
  Option B is the strongest route to smoother animation if latency remains a
  product problem, but adds a frontend build and security/test surface. Option
  C is easiest to test but no longer behaves like a continuously moving
  reflex game.

#### [ ] 21. Build the Bit Fit interface shell

**Deep Blueprint**

- Render question, subject/difficulty, round number, current score, combo,
  timer, Decode button, one row of cipher columns, and clear instructions.
- Use ten columns for answers up to ten characters and add exactly enough
  columns for longer answers, keeping all columns in the same row.
- In each active column, show the revealed clue state above a cycling button;
  show that column's next selectable character directly below its button.
- Ensure inactive columns do not respond to clicks and controls do not shift
  around when the reveal animation changes.
- Keep the Decode action outside the high-frequency fragment and ensure the
  dynamic content below it refreshes in a stable container.
- Verify the one-row layout and mobile behavior with long answers (up to the
  CSV maximum after spaces are removed).

#### [ ] 22. Implement Bit Fit cipher, choices, reveal, cycling, and decode

**Deep Blueprint**

- Normalize the answer according to CSV rules, remove spaces for cipher
  columns, and preserve the original answer for question/result display.
- Generate a random active-column mask with exactly one active column per
  answer character. Map active columns left-to-right to answer order.
- Generate answer-type-correct option pools: A–Z for letters, 0–9 for digits,
  and punctuation choices for a period. Include the correct character and
  enough distractors for the current round's choice count. Initialize each
  player column to a wrong option.
- Use deterministic/injectable randomness in tests. Ensure punctuation
  choices remain valid under the supported CSV answer grammar.
- Build reveal schedules for each active answer character: blank, dash, hash,
  then revealed letter at increasing elapsed times. Keep schedule associated
  with the column independent from player cycling order.
- When a column is cycled, advance to the next option with wraparound. Preview
  the same next option that the callback will select; do not show the
  unrevealed answer as the preview.
- On Decode, concatenate only active player columns left-to-right. If wrong,
  stop timer, record a failed review result, trigger the documented failure
  flow, and do not award clear points. If correct, count revealed answer
  characters, calculate game points and combo, persist the clear exactly once,
  then advance the flow or round.
- Test answer lengths 1/10/11/32, mixed letters/digits/periods, active-column
  mapping, option-type purity, preview cycling/wrap, reveal boundaries,
  wrong decode, correct decode, and persistence idempotence.

#### [ ] 23. Build the Terminal Hacking interface shell

**Deep Blueprint**

- Render question, subject/difficulty, generated terminal dump, attempts left,
  score, combo, elapsed time, password input, submit action, and diagnostic
  log.
- Render exact-match, present-but-misplaced, and absent-character legend.
- Keep the question and diagnostic log stable while input is submitted. After
  a correct answer, make the success notice visible even when the next round
  is prepared.
- Use a form to submit a complete password, disable it once the round is
  over, and ensure each form has a stable unique key.
- Verify that correct, incorrect, blank, duplicate, and invalid guesses each
  have visible feedback and do not leave the browser disconnected.

#### [ ] 24. Implement terminal generation, feedback, attempts, and round advance

**Deep Blueprint**

- Construct a terminal dump from the correct answer plus three wrong answers.
  Place each candidate as a contiguous word in the dump; fill the remaining
  characters from a documented noise alphabet.
- Preserve a minimum dump width of 41 and 20 lines, expanding width for
  answers longer than that width. Ensure every candidate is in bounds and
  appears exactly in the dump.
- Shuffle candidate order. Set attempts to one fewer than the candidate count.
- Normalize guesses by trimming surrounding spaces and uppercasing. Reject
  blank guesses, guesses not among candidate words, and words already in the
  log without consuming a password attempt.
- Compute feedback using character counts: first mark exact-position matches
  and decrement counts; then mark remaining present characters as `#`;
  unmatched positions stay `-`. This avoids overcounting duplicate letters.
- A correct guess records review result, elapsed time, points, combo, and
  clear. If the overall flow target is not complete, create a new question,
  dump, attempt counter, and empty log; preserve a success notice for the
  just-cleared round.
- A wrong valid guess consumes an attempt and adds a feedback row. On the
  final wrong attempt, apply hard-fail combo reset, record failure once, stop
  timer, and expose result/continue controls.
- Test repeated-letter feedback, overlong words, invalid/duplicate guesses,
  correct advancement, final lockout, notice persistence, and repeat callback.

**Architectural divergence point — terminal dump construction**

- **Option A: Generate a fixed number of lines in Python.** Embed each candidate
  in a random row and render with a text/code block. This is simple, testable,
  and works for current answer lengths.
- **Option B: Generate a structured grid model.** Store cells and word
  locations explicitly, then render a grid. This offers future highlighting
  and interaction but creates more layout/state code.
- **Option C: Generate the dump in the browser.** Move noise rendering and
  animation client-side. This can reduce server reruns for elaborate visuals
  but requires a custom frontend component and trust-boundary decisions.
- **Ripple Effect:** Option A is likely smoothest for the current static
  terminal puzzle; the dump is generated once per round and does not need
  per-frame updates. Option B is justified if the UI will point to or highlight
  candidate locations. Option C adds substantial complexity without addressing
  a demonstrated performance bottleneck for the current game.

### Phase 5 — Results, learning, and durable leaderboard

#### [ ] 25. Build the shared game-result interface

**Deep Blueprint**

- Present a result heading and the game-flow completion/failure message.
- Show every question answered in that flow: prompt, chosen answer, correct
  answer, elapsed time, automated rating, and final rating.
- Display the rating selector using descriptive labels (`Again`, `Hard`,
  `Good`, `Easy`) while retaining numeric rating values for logic.
- Provide a single Save Rating and Continue control when review records exist;
  use Continue directly only when there is nothing to save.
- Disable or guard repeated submission and show a durable success or explicit
  failure message. Do not erase review history before persistence succeeds.
- Test empty history, populated history, rating changes, repeated save, and
  continue-to-different-game behavior.

#### [ ] 26. Implement automated review ratings and FSRS persistence

**Deep Blueprint**

- Map each question result to rating 1–4: failures map to Again; wins faster
  than half target to Easy; wins at or under target to Good; slower wins to
  Hard. Validate positive target time.
- Combine automatic and user rating conservatively by taking the lower rating.
- Use FSRS to advance a review card and serialize its state in a stable,
  JSON-compatible shape, including last rating and timestamps.
- Persist the card under player key + question-set id + question key. Update
  scheduling state only after the user confirms the end-of-game rating.
- Treat missing review-card schema as an actionable setup error that names the
  additive migration. Do not hide it behind a success-shaped fallback.
- Test ratings, scheduler state, timezone-aware due/last-review timestamps,
  question-set separation, and missing-table behavior.

**Architectural divergence point — review identity and scheduling**

- **Option A: Key by normalized question text.** Easy to implement and works
  with the current question shape, but editing wording creates a new card and
  exact identity rules need careful definition.
- **Option B: Add stable question IDs.** Each question row gets an immutable
  identifier that survives prompt edits. This is reliable for scheduling but
  requires normalized storage or explicit IDs embedded in CSV.
- **Option C: Key by content hash.** Derive identity from canonical question
  and answers. This requires no visible ID but any content edit intentionally
  resets scheduling and canonicalization must be stable.
- **Ripple Effect:** Option B is best if question editing must preserve review
  history. Option A is the simplest continuation of the current CSV model.
  Option C is an acceptable import-friendly compromise but must define whether
  changing an answer constitutes a new card.

#### [ ] 27. Build the leaderboard interface

**Deep Blueprint**

- Render an ordered table with player display name, lifetime score, and
  completed clears.
- Show empty-state text when there are no players and a clear loading/error
  state when the repository cannot be reached.
- Limit displayed rows (current app uses a maximum of 100 on the dedicated
  leaderboard) and do not expose password fields, review data, or question
  sets.
- Add a homepage preview by reusing the same view model rather than writing a
  second query/render implementation.
- Verify deterministic ordering for tied scores and privacy of returned
  fields.

#### [ ] 28. Implement leaderboard queries and account save reset

**Deep Blueprint**

- Query only the public leaderboard fields, ordered by score descending and
  completed clears descending. Add a stable tie-break field if necessary.
- Parameterize limits and validate their range.
- Implement player reset as an owner-scoped transaction that clears only the
  current player's progress/history as intended, not their credentials or
  other players' data.
- Decide explicitly whether question-set review cards are also reset; the
  current reset semantics should be inspected and preserved or intentionally
  changed.
- Test score ordering, ties, empty results, limit, current-player isolation,
  and transaction rollback.

#### [ ] 29. Rebuild static information pages and content

**Deep Blueprint**

- Recreate About and Source pages as simple renderers in the central routing
  system. Keep external media and links optional so an unavailable third-party
  host cannot break the game shell.
- Update the project description so it accurately explains the three games,
  the question-set workflow, scoring/rank behavior, and that the app is a
  prototype.
- Ensure the displayed version and deployment claims match the implemented
  code; avoid stale claims about rounds, scoring, or persistence.
- Verify direct route access and navigation back to Homepage.

### Phase 6 — Hardening, migration, and release

#### [ ] 30. Create a complete test pyramid for the rebuilt behavior

**Deep Blueprint**

- Keep fast unit tests for CSV parsing, question selection, feedback, movement,
  scoring, rank, timer, and review logic. These functions should not import or
  call Streamlit.
- Add application-service tests for registration/login, set ownership, result
  persistence, reset, and migration error reporting using an isolated
  database or repository fake.
- Add UI tests for login/register, navigation, form submission, validation,
  result review, and all game transitions. Prefer Streamlit's supported app
  testing tools where applicable.
- Add browser smoke tests for the Slider fragment, Bit Fit reveal/cycling,
  Hacking correct/wrong/final-attempt transitions, and session reconnect.
- Use seeded randomness or injected generators for deterministic scenarios.
- Check that no test imports production credentials or connects to a real
  Supabase project. Run tests using temporary isolated data.
- Run the complete suite after each vertical slice and before release.

#### [ ] 31. Add observability and actionable error handling

**Deep Blueprint**

- Define expected error categories: form validation, not found/unauthorized,
  duplicate name, missing configuration, unavailable database, missing schema,
  and unexpected internal error.
- Show user-safe messages in the UI. Log technical details server-side without
  logging passwords, database URIs, session cookies, or full sensitive CSV
  content.
- Do not catch every exception and continue with default/empty state. Catch
  known expected failures at the UI/application boundary and allow unexpected
  failures to remain visible in development logs.
- Add request/action identifiers or contextual log fields for account, route,
  game, and round where safe; avoid including secrets or answer content unless
  needed and permitted.
- Exercise missing `SUPABASE_DB_URL`, unavailable database, and undefined
  table cases in a non-production environment.

#### [ ] 32. Prepare configuration, schema, and deployment

**Deep Blueprint**

- Declare runtime dependencies and supported Python version in the manifest.
  Install only from that manifest in a clean environment.
- Read `SUPABASE_DB_URL` from environment variables or the deployment secret
  store. Keep `.env` and Streamlit secrets out of Git; retain only a
  placeholder `.env.example`.
- Keep database migrations explicit, ordered, reviewed, and separately
  executable. Ensure app startup never silently creates or rewrites schema.
- For a fresh empty database, apply the complete baseline schema then all
  additive migrations. For an existing database, inspect its current schema
  and apply only missing additive migrations. Back up important data before
  any migration.
- For Streamlit Community Cloud, configure the secret in app settings and
  reboot. For a Linux service, use a protected environment file and bind
  Streamlit to localhost behind a TLS reverse proxy.
- Verify a fresh install, account creation, login, question set creation,
  round completion, review persistence, and leaderboard update against a
  staging database before release.

**Architectural divergence point — deployment/data access**

- **Option A: Streamlit directly connects to PostgreSQL.** This matches the
  current app and avoids an extra service. Use parameterized SQL, short
  connection lifetimes, transactions, and server-side secrets.
- **Option B: Put an application API between Streamlit and PostgreSQL.**
  Streamlit calls a backend service that owns business rules and database
  access. This supports multiple clients and central authorization, but adds
  deployment, API contracts, and network failure paths.
- **Option C: Move to a managed backend/data service.** Use its authentication
  and database APIs. This may reduce operations work but introduces provider
  coupling and requires careful review of authorization policies.
- **Ripple Effect:** Option A is simplest for a single Streamlit application
  and small traffic, but connections and database work must remain bounded.
  Option B pays off if a mobile/web client or independent backend is planned.
  Option C can accelerate setup but security depends on correct server-side
  policy; never expose privileged database credentials to the browser.

#### [ ] 33. Cut over to the rewrite without losing data

**Deep Blueprint**

- Keep the old implementation available until the replacement has passed
  staging acceptance. Do not overwrite the only working copy before tests and
  backups exist.
- Compare old/new question parsing, player totals, question-set ownership,
  active set selection, score writes, and review records on a copied staging
  dataset.
- If the new schema changes, write an explicit one-way or reversible migration
  strategy and test it on a copy of production data first.
- Do not reset, truncate, or reseed an existing Supabase database as a
  shortcut. Keep account and player-progress records intact.
- Cut over by deploying the new entry point after staging verification, then
  monitor login, game completion, and persistence errors.
- Preserve a documented rollback route to the prior release and compatible
  schema.

## Definition of done

- A new user can register, log in, select/edit a private question set, and
  complete all three games.
- The game flow starts with the delay/countdown, advances on success, ends on
  failure or target completion, shows results, persists review ratings, and
  waits for explicit Continue.
- Slider timing and one-refresh-tick grace, Bit Fit reveal/cycling/type
  constraints, and Hacking feedback/attempts all have unit and browser
  coverage.
- Score, combo, rank, clear count, review cards, and leaderboard remain
  consistent after reruns and reloads.
- No credentials are committed; account data is isolated by owner; expected
  failures are visible and actionable.
- Existing data has a tested migration/cutover plan, and all tests pass in an
  isolated environment.

## First practical move

Before replacing anything, create a separate rewrite branch or worktree, keep
the current application as a reference, and finish Step 1 only. Do not begin
by rewriting all modules at once. The learning goal is to complete one small,
visible, testable vertical slice at a time.
