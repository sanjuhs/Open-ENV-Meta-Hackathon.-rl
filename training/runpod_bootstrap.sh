#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-/workspace/open-env-meta}"
REPO_URL="${REPO_URL:-https://github.com/sanjuhs/Open-ENV-Meta-Hackathon.-rl.git}"

apt-get update -y
apt-get install -y git
pip3 install datasets peft trl sentencepiece

mkdir -p /workspace
if [[ ! -d "${ROOT_DIR}" ]]; then
  git clone "${REPO_URL}" "${ROOT_DIR}"
fi

cd "${ROOT_DIR}"
python3 training/download_models.py --models tiny medium experimental
