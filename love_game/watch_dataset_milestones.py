#!/usr/bin/env python3
"""Watch Love Game dataset token totals and upload milestone snapshots to Hugging Face."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from love_game.common import DATASETS_DIR, list_dataset_files, load_env_key, read_jsonl


DEFAULT_MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
DEFAULT_REPO = "sanjuhs/adt-personality-dataset"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", default=DEFAULT_REPO)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--milestones", default="1000000,2000000,5000000")
    parser.add_argument("--tokenizer-model", default=DEFAULT_MODEL)
    parser.add_argument("--hf-token-env", default="HF_TOKEN")
    parser.add_argument("--workspace", type=Path, default=ROOT)
    return parser


def combined_tokens(tokenizer) -> tuple[int, dict[str, int]]:
    per_file: dict[str, int] = {}
    total = 0
    for path in list_dataset_files():
        rows = read_jsonl(path)
        token_total = 0
        for row in rows:
            token_total += len(tokenizer(json.dumps(row, ensure_ascii=False), add_special_tokens=False)["input_ids"])
        per_file[path.name] = token_total
        total += token_total
    return total, per_file


def run(command: list[str], cwd: Path, env: dict[str, str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n=== RUN {' '.join(command)} ===\n")
        handle.flush()
        proc = subprocess.run(command, cwd=cwd, env=env, stdout=handle, stderr=subprocess.STDOUT)
    return proc.returncode


def main() -> None:
    args = build_parser().parse_args()
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer_model, trust_remote_code=True)
    milestones = sorted({int(item.strip()) for item in args.milestones.split(",") if item.strip()})
    runs_dir = args.workspace / "love_game" / "milestone_runs"
    uploads_dir = args.workspace / "love_game" / "dataset_uploads"
    runs_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    state_path = runs_dir / "milestone_state.json"
    hf_token = load_env_key(args.hf_token_env)
    env = dict(os.environ)
    env["HF_TOKEN"] = hf_token

    while True:
        total, per_file = combined_tokens(tokenizer)
        state = {"combined_tokens": total, "per_file_tokens": per_file, "milestones": {}}
        uploaded_any = False

        for milestone in milestones:
            upload_dir = uploads_dir / f"snapshot_{milestone}"
            marker_path = upload_dir / ".uploaded"
            uploaded = marker_path.exists()
            reached = total >= milestone
            state["milestones"][str(milestone)] = {"reached": reached, "uploaded": uploaded}
            if reached and not uploaded:
                export_rc = run(
                    [
                        "python3",
                        "love_game/export_dataset_snapshot.py",
                        "--output-dir",
                        str(upload_dir),
                        "--repo-id",
                        args.repo_id,
                        "--milestone",
                        str(milestone),
                    ],
                    cwd=args.workspace,
                    env=env,
                    log_path=runs_dir / "milestone_uploader.log",
                )
                create_rc = run(
                    [
                        "hf",
                        "repo",
                        "create",
                        args.repo_id,
                        "--repo-type",
                        "dataset",
                        "--exist-ok",
                        "--token",
                        hf_token,
                    ],
                    cwd=args.workspace,
                    env=env,
                    log_path=runs_dir / "milestone_uploader.log",
                )
                upload_rc = run(
                    [
                        "hf",
                        "upload-large-folder",
                        args.repo_id,
                        str(upload_dir),
                        "--repo-type",
                        "dataset",
                        "--token",
                        hf_token,
                    ],
                    cwd=args.workspace,
                    env=env,
                    log_path=runs_dir / "milestone_uploader.log",
                )
                if export_rc == 0 and create_rc == 0 and upload_rc == 0:
                    marker_path.write_text("uploaded\n", encoding="utf-8")
                uploaded_any = True

        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(json.dumps(state), flush=True)
        time.sleep(10 if uploaded_any else args.poll_seconds)


if __name__ == "__main__":
    main()
