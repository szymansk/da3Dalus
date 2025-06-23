#!/bin/bash
docker compose run --rm \
  --entrypoint "" \
  -w /home/cadquery/workspace \
  cq-client \
  /opt/anaconda/envs/cadquery/bin/python3 -m unittest discover \
    -s app/tests \
    -p "test*.py" \
    -t .