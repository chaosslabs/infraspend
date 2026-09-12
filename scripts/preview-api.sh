#!/usr/bin/env bash
# Run from the repository root. Project contains only disposable preview services.
set -euo pipefail
: "${RAILWAY_API_TOKEN:?Missing RAILWAY_API_TOKEN}"
: "${PR_NUMBER:?Missing PR_NUMBER}"
[[ "$PR_NUMBER" =~ ^[0-9]+$ ]] || exit 1
project=50f0bb69-50f9-49cd-9b65-132436447fe6
base=3361497b-88c2-4d0d-8908-85ccac0cd0ec
environment="pr-$PR_NUMBER"
railway link --project "$project" --environment "$base" --service api
existing=$(railway environment list --json | jq -r --arg name "$environment" '.environments[] | select(.name == $name) | .id')
if [[ "${1:-deploy}" == cleanup ]]; then
  if [[ -n "$existing" ]]; then
    railway environment delete "$existing" --yes
  fi
  exit 0
fi
: "${PREVIEW_COMMIT:?Missing PREVIEW_COMMIT}"
if [[ -z "$existing" ]]; then
  railway environment new "$environment" --copy "$base" --json
fi
railway link --project "$project" --environment "$environment" --service api
railway variable set --service api --skip-deploys "PREVIEW_COMMIT=$PREVIEW_COMMIT"
domain_json=$(railway domain --service api --port 8000 --json)
backend=$(jq -er '.domain' <<< "$domain_json")
[[ "$backend" == https://* ]] || backend="https://$backend"
[[ "$backend" =~ ^https://[a-z0-9-]+\.up\.railway\.app$ ]] || { echo 'Invalid Railway domain'; exit 1; }
railway up api --path-as-root --service api --environment "$environment" --ci
for attempt in $(seq 1 90); do
  if curl --silent --fail --max-time 10 "$backend/health" | jq -e --arg commit "$PREVIEW_COMMIT" '.status == "ok" and .sandbox == true and .commit == $commit' > /dev/null; then
    printf 'backend_url=%s\n' "$backend" >> "$GITHUB_OUTPUT"
    exit 0
  fi
  sleep 5
done
echo 'Preview API did not become healthy at the requested commit' >&2
exit 1
