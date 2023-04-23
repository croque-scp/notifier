#!/usr/bin/env sh

set -e

docker build --target execute_lambda --tag notifier:execute_lambda --tag 288611151503.dkr.ecr.eu-west-2.amazonaws.com/wikidot_notifier:latest .
aws ecr get-login-password --region eu-west-2 --profile notifier | docker login --username AWS --password-stdin 288611151503.dkr.ecr.eu-west-2.amazonaws.com
docker push 288611151503.dkr.ecr.eu-west-2.amazonaws.com/wikidot_notifier:latest

echo "Next steps:"
echo "In Lambda, re-select the new image as the Lambda image"
echo "In ECR, delete old untagged images"