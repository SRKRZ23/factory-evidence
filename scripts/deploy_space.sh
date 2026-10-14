#!/bin/bash
# Deploy the current commit to the Hugging Face Space ZeroR3/factory-evidence (Docker SDK).
set -euo pipefail
cd "$(dirname "$0")/.."
SPACE=${SPACE:-ZeroR3/factory-evidence}
TMP=$(mktemp -d)
git archive HEAD | tar -x -C "$TMP"
{ cat <<HDR
---
title: Factory Evidence
emoji: 🏭
colorFrom: red
colorTo: gray
sdk: docker
app_port: 8080
pinned: false
license: mit
short_description: Supplier docs → verified CBAM savings · open models on AMD
---

HDR
  cat README.md; } > "$TMP/README.md"
hf repo create "$SPACE" --repo-type space --space_sdk docker --exist-ok >/dev/null 2>&1 || true
hf upload "$SPACE" "$TMP" . --repo-type space --commit-message "deploy $(git rev-parse --short HEAD)" 2>&1 | tail -2
rm -rf "$TMP"
echo "https://huggingface.co/spaces/$SPACE"
