#!/bin/sh
set -eu
cp /tmp/answers.json /logs/verifier/answers.json
python3 /tests/score.py /tmp/answers.json /tests/labels.json /app/corpus.json > /logs/verifier/reward.json
