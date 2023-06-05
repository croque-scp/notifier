#!/usr/bin/env sh

cleanup() {
  docker compose -f docker-compose.test.yml down
}
trap cleanup EXIT

docker compose -f docker-compose.test.yml up --build notifier --attach notifier --attach database --exit-code-from notifier