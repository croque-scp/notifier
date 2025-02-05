#!/usr/bin/env sh

set -e

docker build --target execute_lambda --tag notifier:execute_lambda --tag 288611151503.dkr.ecr.eu-west-2.amazonaws.com/wikidot_notifier:latest --provenance false .

aws ecr get-login-password --region eu-west-2 --profile notifier | docker login --username AWS --password-stdin 288611151503.dkr.ecr.eu-west-2.amazonaws.com

docker push 288611151503.dkr.ecr.eu-west-2.amazonaws.com/wikidot_notifier:latest

aws lambda update-function-code --function-name WikidotNotifier --image-uri 288611151503.dkr.ecr.eu-west-2.amazonaws.com/wikidot_notifier:latest --region eu-west-2 --profile notifier
