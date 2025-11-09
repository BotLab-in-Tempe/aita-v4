#!/usr/bin/env bash
set -euo pipefail

cd /opt/aita/aita-v4

echo "===> Pulling latest aita-v4 code..."
git pull

echo "===> Rebuilding and restarting aita-v4 stack..."
docker compose down
docker compose up -d --build

echo "===> Current containers:"
docker compose ps

echo "===> Tail logs (Ctrl+C to stop)..."
docker logs -f aita-v4