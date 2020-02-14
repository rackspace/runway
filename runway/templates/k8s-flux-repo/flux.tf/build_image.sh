#!/bin/sh
docker build --tag $1:1.15.0 .
$(aws ecr get-login --no-include-email --region us-east-1)
docker push $1:1.15.0