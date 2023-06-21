#!/usr/bin/env sh

service=notifier
if [ "$1" = "--no-db" ]; then
  service=notifier_without_db
fi

cleanup() {
  docker compose -f docker-compose.test.yml down
}
trap cleanup EXIT

docker compose -f docker-compose.test.yml up --build $service --attach $service --attach database --exit-code-from $service