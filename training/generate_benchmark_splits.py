#!/usr/bin/env python3
"""Generate deterministic benchmark manifests for DocEdit Game V2."""

from __future__ import annotations

import json
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DOCEDIT_DIR = ROOT / "attempt1" / "doc_edit_game_v2"
if str(DOCEDIT_DIR) not in sys.path:
    sys.path.insert(0, str(DOCEDIT_DIR))

from game.generator import generate_task  # noqa: E402


MANIFEST_DIR = ROOT / "training" / "manifests"
BENCHMARK_VERSION = "docedit_benchmark_v1"


@dataclass(frozen=True)
class SplitConfig:
    name: str
    cases_per_pair: int
    base_doc_seed: int
    base_corruption_seed: int


@dataclass(frozen=True)
class BenchmarkCase:
    split: str
    case_id: str
    doc_seed: int
    corruption_seed: int
    difficulty: int
    domain: str
    doc_type: str
    corruption_count: int
    corruption_types: list[str]
    instruction: str
    max_steps: int


SPLITS: tuple[SplitConfig, ...] = (
    SplitConfig(name="train", cases_per_pair=8, base_doc_seed=100_000, base_corruption_seed=900_000),
    SplitConfig(name="validation", cases_per_pair=2, base_doc_seed=200_000, base_corruption_seed=1_900_000),
    SplitConfig(name="test", cases_per_pair=2, base_doc_seed=300_000, base_corruption_seed=2_900_000),
)

DOMAINS: tuple[str, ...] = ("legal", "pharma", "business")
DIFFICULTIES: tuple[int, ...] = (1, 2, 3, 4, 5, 6)


def _iter_cases(config: SplitConfig) -> Iterable[BenchmarkCase]:
    rng = random.Random(config.base_doc_seed + config.base_corruption_seed)
    offset = 0

    for domain in DOMAINS:
        for difficulty in DIFFICULTIES:
            for pair_index in range(config.cases_per_pair):
                doc_seed = config.base_doc_seed + offset
                corruption_seed = config.base_corruption_seed + rng.randint(10_000, 9_999_999)
                task = generate_task(
                    doc_seed=doc_seed,
                    corruption_seed=corruption_seed,
                    difficulty=difficulty,
                    domain=domain,
                )
                case_id = (
                    f"{config.name}_{domain}_d{difficulty}_"
                    f"{pair_index:02d}_doc{doc_seed}_corr{corruption_seed}"
                )
                yield BenchmarkCase(
                    split=config.name,
                    case_id=case_id,
                    doc_seed=doc_seed,
                    corruption_seed=corruption_seed,
                    difficulty=difficulty,
                    domain=domain,
                    doc_type=task["doc_type"],
                    corruption_count=task["corruption_count"],
                    corruption_types=list(task["corruption_types_used"]),
                    instruction=task["instruction"],
                    max_steps=task["max_steps"],
                )
                offset += 1


def build_manifest() -> dict:
    splits: dict[str, list[dict]] = {}
    for split in SPLITS:
        splits[split.name] = [asdict(case) for case in _iter_cases(split)]

    return {
        "benchmark_version": BENCHMARK_VERSION,
        "domains": list(DOMAINS),
        "difficulties": list(DIFFICULTIES),
        "splits": splits,
    }


def main() -> None:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    output_path = MANIFEST_DIR / f"{BENCHMARK_VERSION}.json"
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    for split_name, cases in manifest["splits"].items():
        print(f"  {split_name}: {len(cases)} cases")


if __name__ == "__main__":
    main()
