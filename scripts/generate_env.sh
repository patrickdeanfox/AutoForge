#!/bin/bash
# Generates .env from pass store. Run this after any secret rotation.
# Output written to ~/autoforge/.env — never committed to git.

set -e

OUTFILE="$(dirname "$0")/../.env"

echo "# AutoForge .env — generated $(date)" > "$OUTFILE"
echo "# Do not commit this file. Regenerate with scripts/generate_env.sh" >> "$OUTFILE"
echo "" >> "$OUTFILE"

echo "ANTHROPIC_API_KEY=$(pass autoforge/anthropic_api_key)" >> "$OUTFILE"
echo "POSTGRES_PASSWORD=$(pass autoforge/postgres_password)" >> "$OUTFILE"
echo "DATABASE_URL=postgresql+asyncpg://autoforge:$(pass autoforge/postgres_password)@localhost:5432/autoforge" >> "$OUTFILE"
echo "REDIS_URL=redis://localhost:6379/0" >> "$OUTFILE"
echo "GITHUB_TOKEN=$(pass autoforge/github_token)" >> "$OUTFILE"
echo "GITHUB_ORG=yourusername" >> "$OUTFILE"
echo "TELEGRAM_BOT_TOKEN=$(pass autoforge/telegram_bot_token)" >> "$OUTFILE"
echo "TELEGRAM_CHAT_ID=$(pass autoforge/telegram_chat_id)" >> "$OUTFILE"
echo "SECRET_KEY=$(pass autoforge/secret_key)" >> "$OUTFILE"
echo "ENVIRONMENT=development" >> "$OUTFILE"
echo "LOG_LEVEL=INFO" >> "$OUTFILE"

chmod 600 "$OUTFILE"
echo ".env written to $OUTFILE"
