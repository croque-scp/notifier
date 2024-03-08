#!/usr/bin/env sh

service="notifier --attach database"
if [ "$1" = "--no-db" ]; then
  service=notifier_without_db
fi

cleanup() {
  docker compose -f docker-compose.test.yml down
}
trap cleanup EXIT

docker compose -f docker-compose.test.yml up --build $service --attach $service --exit-code-from $service