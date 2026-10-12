# Supabase and Linux deployment

The app connects directly to Supabase PostgreSQL from the Streamlit server. The
database URL is a server secret; never put it in browser code, commit it, or
expose it to users. Use the Supabase **Session pooler** connection string for a
long-running Linux server and require SSL.

## Prepare Supabase

1. Create a Supabase project and keep its database password private.
2. Open the Supabase SQL Editor and run
   [`supabase/migrations/20261011000000_create_game_tables.sql`](./supabase/migrations/20261011000000_create_game_tables.sql).
3. In the project Connect dialog, copy the Session pooler URI and replace its
   password placeholder with the database password. The URI must include
   `sslmode=require`.

## Deploy on Streamlit Community Cloud

First, run the migration from the Supabase SQL Editor as described above. In
Supabase's **Connect** dialog, copy the PostgreSQL connection URI and make sure
it includes `sslmode=require`.

In Streamlit Community Cloud, open the deployed app's menu, choose **Settings →
Secrets**, and add the URI as a TOML string:

```toml
SUPABASE_DB_URL = "postgresql://..."
```

Save the secret and reboot the app. The app reads it from `st.secrets`; never
put the URI in source code, commit it, or paste it into chat. App restarts then
reconnect to the same Supabase database instead of relying on the app's local
filesystem.

## Install on a persistent Linux host

Copy the repository to `/opt/nierva-game` on a Linux server with Python 3.10 or
newer, then run:

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

The service listens only on `127.0.0.1:8501`. Put it behind a TLS-enabled
reverse proxy (for example, Nginx or Caddy) before making it reachable on the
internet. Review firewall rules so the database and Streamlit port are not
publicly exposed.

## Move existing local SQLite data

After applying the schema and installing dependencies, copy the existing
`nierva_players.sqlite3` file to the server without committing it. Run the
one-time importer before starting the app:

```sh
sudo -u nierva env SUPABASE_DB_URL='postgresql://...' \
  /opt/nierva-game/.venv/bin/python \
  /opt/nierva-game/scripts/migrate_sqlite_to_supabase.py \
  /opt/nierva-game/nierva_players.sqlite3
```

The importer refuses to write if the Supabase `players` table is not empty, and
copies accounts, saved question sets, and clear history in one database
transaction. Keep the local file as a backup until the migrated accounts and
scores have been verified. Do not place the connection URI directly in shell
history on a shared server; use a protected environment file instead.
