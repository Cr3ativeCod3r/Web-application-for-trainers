#!/usr/bin/env sh
# One-off migration for deployments created before the chat service had its own
# database: copies chat_rooms/chat_messages from the main database into the chat
# database, then drops them from the main one.
#
# Usage: MAIN_DB_URL=postgres://... CHAT_DB_URL=postgres://... ./scripts/move_chat_tables.sh
#
# Run it with the chat service stopped. Afterwards start the chat service (it runs
# `alembic upgrade head`, which adds chat_users) and run
# `python manage.py publish_user_snapshots` so the chat service learns about users.
set -eu

: "${MAIN_DB_URL:?MAIN_DB_URL is required}"
: "${CHAT_DB_URL:?CHAT_DB_URL is required}"

pg_dump --no-owner --no-acl -t chat_rooms -t chat_messages -t alembic_version "$MAIN_DB_URL" \
  | psql --single-transaction -v ON_ERROR_STOP=1 "$CHAT_DB_URL"

psql -v ON_ERROR_STOP=1 "$MAIN_DB_URL" -c "DROP TABLE chat_messages, chat_rooms, alembic_version"
echo "Chat tables moved."
