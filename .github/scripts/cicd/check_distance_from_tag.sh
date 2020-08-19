#!/usr/bin/env bash

# Checks for this distance from the last tag.
# If there is no distence, return a non-zero exit code.
#
# This can be used in GitHub actions with the following steps using conditionals to handle either case.
#
# Example:
#
#   - id: check_distance
#     continue-on-error: true
#     run: bash ./check_distance_from_tag.sh
#     working-directory: .github/scripts/cicd
#   - if: steps.check_distance.outcome == 'failure'
#     run: echo "No distance"
#   - if: steps.check_distance.outcome == 'success'
#     run: echo "There is distance"

DESCRIBE=`git describe --tags --match "v*.*.*"`
echo "Result from 'git describe': ${DESCRIBE}"
DISTANCE=`echo ${DESCRIBE} | grep -P '\-(\d)*\-g(\d)*'`
if [ -n "${DISTANCE}" ]; then
    echo "Distance from last tag detected: ${DISTANCE}"
    echo "It is safe to proceed with a pre-production release."
    exit 0
else
    echo "No distance from last tag; skipping pre-production release."
    exit 1
fi
