#!/usr/bin/env bash
# Regression gate: every "good" results dir must validate clean, and the
# deliberately-broken fixtures must still fail (proves the check has teeth,
# not just that nothing is wrong). Run locally the same way CI runs it.
set -uo pipefail

FAILED=0

assert_clean () {
  echo "--- validate: $1 (expect 0 errors) ---"
  python scripts/validate.py --results "$1"
  if [ $? -ne 0 ]; then
    echo "FAIL: expected $1 to validate clean"
    FAILED=1
  fi
}

assert_fails () {
  echo "--- validate: $1 (expect errors -- proves the check has teeth) ---"
  python scripts/validate.py --results "$1"
  if [ $? -eq 0 ]; then
    echo "FAIL: expected $1 to be rejected, but validator passed it"
    FAILED=1
  fi
}

assert_clean results/claude-sonnet-5
assert_clean results/claude-opus-4-8
assert_clean results/glm-4.6
assert_clean benchmark/results/claude-sonnet-5

assert_fails tests/bad_examples

echo "--- score.py (informational) ---"
python scripts/score.py --results-root results

echo "--- score_recall.py (informational) ---"
python benchmark/scripts/score_recall.py --model claude-sonnet-5

# robustness/ is NOT gated: naive validate.py is EXPECTED to fail 2/3 here
# by design (that's the finding -- see README section 7). It's run here
# only via check_grounding_modes.py, which is the tag-aware checker that
# should show 3/3.
echo "--- check_grounding_modes.py (gated: tag-aware grounding must be 3/3) ---"
ROBUSTNESS_OUT="$(python robustness/scripts/check_grounding_modes.py --model claude-sonnet-5)"
echo "$ROBUSTNESS_OUT"
if ! echo "$ROBUSTNESS_OUT" | grep -q "Tag-aware grounding: 3/3"; then
  echo "FAIL: expected tag-aware grounding to be 3/3 on robustness cases"
  FAILED=1
fi

echo "--- check_negatives.py (gated: hard negative controls must stay at zero) ---"
python negative_controls/scripts/check_negatives.py --model claude-sonnet-5
if [ $? -ne 0 ]; then
  echo "FAIL: expected zero false positives on negative_controls cases"
  FAILED=1
fi

if [ "$FAILED" -ne 0 ]; then
  echo "CI CHECK FAILED"
  exit 1
fi
echo "CI CHECK PASSED"
