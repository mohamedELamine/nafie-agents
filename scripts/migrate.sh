#!/bin/bash
set -e
psql "$DATABASE_URL" -f scripts/init_db.sql
echo "Migration complete"
