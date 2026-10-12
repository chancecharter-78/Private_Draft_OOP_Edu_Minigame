# Supabase deployment

The app stores accounts, scores, completed rounds, and question sets directly
in Supabase PostgreSQL. It does not use a local SQLite database. The database
URL is a server secret; never put it in browser code, commit it, or expose it
to users.

## Initialize the Supabase database

1. Create a Supabase project and keep its database password private.
2. Open the Supabase SQL Editor and run the schema setup file once:
   [`supabase/migrations/20261011000000_create_game_tables.sql`](./supabase/migrations/20261011000000_create_game_tables.sql).
   This creates the tables and indexes the app needs; it is not a data import.
3. In the project's **Connect** dialog, copy a PostgreSQL connection URI and
   make sure it includes `sslmode=require`.

New accounts and game progress are written straight to this Supabase database.
No SQLite setup or SQLite-to-Supabase import is needed.

## Deploy on Streamlit Community Cloud

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

Use this option only if hosting Streamlit on your own persistent Linux server.
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
publicly exposed. Do not place the connection URI directly in shell history on
a shared server; use the protected environment file instead.
