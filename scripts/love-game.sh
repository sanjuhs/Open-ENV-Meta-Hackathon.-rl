#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CMD="${1:-help}"
shift || true

case "$CMD" in
  split)
    python3 love_game/build_training_splits.py "$@"
    ;;
  viewer)
    python3 love_game/dataset_viewer.py "$@"
    ;;
  prepare)
    python3 love_game/prepare_training_sets.py "$@"
    ;;
  count-tokens)
    python3 love_game/count_tokens.py "$@"
    ;;
  scale)
    python3 love_game/scale_corpus.py "$@"
    ;;
  auto-pipeline)
    python3 love_game/auto_pipeline.py "$@"
    ;;
  generate-more)
    python3 love_game/expand_datasets.py "$@"
    ;;
  train-rm)
    python3 love_game/train_reward_model.py "$@"
    ;;
  train-rm-neural)
    python3 love_game/run_reward_model_transformer.py "$@"
    ;;
  train-rm-ppo)
    python3 love_game/run_reward_model_ppo.py "$@"
    ;;
  train-sft)
    python3 love_game/run_sft_full.py "$@"
    ;;
  train-dpo)
    python3 love_game/run_dpo_full.py "$@"
    ;;
  train-grpo)
    python3 love_game/run_grpo.py "$@"
    ;;
  train-ppo)
    python3 love_game/run_ppo.py "$@"
    ;;
  report)
    python3 love_game/build_snapshot_report.py "$@"
    ;;
  local-infer)
    python3 love_game/run_local_inference_suite.py "$@"
    ;;
  upload-hf)
    python3 love_game/upload_snapshot_to_hf.py "$@"
    ;;
  plot)
    python3 love_game/plot_training_metrics.py "$@"
    ;;
  sample)
    python3 love_game/sample_generations.py "$@"
    ;;
  all)
    python3 love_game/prepare_training_sets.py
    python3 love_game/train_reward_model.py "$@"
    ;;
  *)
    cat <<'EOF'
Usage:
  ./scripts/love-game.sh split
  ./scripts/love-game.sh viewer
  ./scripts/love-game.sh prepare
  ./scripts/love-game.sh count-tokens
  ./scripts/love-game.sh scale [args...]
  ./scripts/love-game.sh auto-pipeline [args...]
  ./scripts/love-game.sh generate-more [args...]
  ./scripts/love-game.sh train-rm [args...]
  ./scripts/love-game.sh train-rm-neural [args...]
  ./scripts/love-game.sh train-rm-ppo [args...]
  ./scripts/love-game.sh train-sft [args...]
  ./scripts/love-game.sh train-dpo [args...]
  ./scripts/love-game.sh train-grpo [args...]
  ./scripts/love-game.sh train-ppo [args...]
  ./scripts/love-game.sh report [args...]
  ./scripts/love-game.sh local-infer [args...]
  ./scripts/love-game.sh upload-hf [args...]
  ./scripts/love-game.sh plot [args...]
  ./scripts/love-game.sh sample [args...]
  ./scripts/love-game.sh all
EOF
    ;;
esac
