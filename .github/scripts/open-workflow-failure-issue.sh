#!/usr/bin/env bash
# Open or update one open GitHub issue labeled workflow-failure.
# Uses the workflow's GITHUB_TOKEN (passed as GH_TOKEN). No extra secrets.
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${WORKFLOW_NAME:?WORKFLOW_NAME is required}"
: "${RUN_URL:?RUN_URL is required}"

label="workflow-failure"
title="workflow-failure: ${WORKFLOW_NAME}"

if ! gh label list --limit 200 --json name --jq '.[].name' | grep -Fxq "$label"; then
  gh label create "$label" --color B60205 --description "Scheduled workflow failed after retries"
fi

body=$(cat <<EOF
The workflow \`${WORKFLOW_NAME}\` failed after retries. Previous data files were left in place, and this run did not push a partial snapshot.

- Run: ${RUN_URL}
- Event: ${RUN_EVENT:-unknown}
- Ref: ${RUN_REF:-unknown}
- SHA: ${RUN_SHA:-unknown}
EOF
)

existing=""
while IFS=$'\t' read -r number issue_title; do
  if [ "$issue_title" = "$title" ]; then
    existing="$number"
    break
  fi
done < <(gh issue list --state open --label "$label" --limit 100 --json number,title --jq '.[] | [.number, .title] | @tsv')

if [ -n "$existing" ]; then
  gh issue comment "$existing" --body "$body"
  echo "Updated issue #${existing}"
else
  url="$(gh issue create --title "$title" --label "$label" --body "$body")"
  echo "Opened ${url}"
fi
