#!/usr/bin/env python3
"""Upload a Love Game snapshot bundle to Hugging Face Hub using the Python API."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="HF repo id, e.g. sanjuhs/love-game-models")
    parser.add_argument("--folder", type=Path, required=True, help="Local folder to upload")
    parser.add_argument("--repo-type", default="model", choices=["model", "dataset", "space"])
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"))
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--commit-message", default="Upload Love Game snapshot")
    args = parser.parse_args()

    if not args.folder.exists():
        raise SystemExit(f"Missing upload folder: {args.folder}")
    if not args.token:
        raise SystemExit("Missing HF token. Pass --token or set HF_TOKEN.")

    from huggingface_hub import HfApi

    api = HfApi(token=args.token)
    api.create_repo(
        repo_id=args.repo,
        repo_type=args.repo_type,
        private=args.private,
        exist_ok=True,
    )
    api.upload_folder(
        repo_id=args.repo,
        repo_type=args.repo_type,
        folder_path=str(args.folder),
        commit_message=args.commit_message,
    )
    print(f"https://huggingface.co/{'datasets/' if args.repo_type == 'dataset' else ''}{args.repo}")


if __name__ == "__main__":
    main()
