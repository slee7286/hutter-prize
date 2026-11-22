#!/bin/sh
# Run from the project root. Publish only the completed, byte-verified summary.
set -eu
python3 research/tools/starlit_trial.py
result=research/experiments/starlit-order-result.json
test "$(git branch --show-current)" = main
test ! -e "$result"
cp build/starlit-trial/final.json "$result"
git add -- "$result"
git commit --only -m 'Report measured STARLIT ordering gains and prediction error' -- "$result"
git push origin main:main
test "$(git rev-parse HEAD)" = "$(git ls-remote origin refs/heads/main | cut -f1)"
