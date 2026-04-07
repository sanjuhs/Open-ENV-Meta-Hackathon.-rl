"""
Baseline inference script for DocEdit Game V2.
Runs an OpenAI-compatible LLM against the 5 fixed evaluation tasks.

Required env vars: API_BASE_URL, MODEL_NAME, HF_TOKEN
"""

import asyncio
import json
import os
from typing import List, Optional

from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
API_KEY = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

HF_REPO_ID = "sanjuhs/doc_edit_v3"
BENCHMARK = "doc_edit_game_v2"
TASKS = ["legal_easy", "legal_medium", "legal_hard", "pharma_easy", "pharma_hard"]
SUCCESS_THRESHOLD = 0.90


def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str] = None):
    error_val = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


SYSTEM_PROMPT = """You are an expert document editor AI. You receive a document chunk (XML-tagged) and an edit instruction.

You must respond with a JSON object representing ONE tool call:
{
  "tool": "<tool_name>",
  "params": { ... tool-specific parameters ... }
}

Available tools:
- replace: {"target": "exact text to find", "content": "replacement text"}
- insert: {"position": line_index, "content": "new paragraph text"}
- delete: {"target": "text in paragraph to delete"}
- format_text: {"target": "text to format", "format": "bold|italic|underline|uppercase|lowercase"}
- highlight: {"target": "text to highlight", "color": "yellow|green|red|blue"}
- set_alignment: {"line_index": N, "alignment": "left|center|right|justify"}
- set_spacing: {"line_index": N, "spacing_after": "6|12|18|24"}
- clean_junk_chars: {} (removes all invisible junk characters)
- merge_runs: {"line_index": N} (merges fragmented PDF conversion runs)
- move: {"target": "text in paragraph to move", "position": new_line_index}
- add_redline: {"target": "text to mark", "new_text": "proposed replacement"}
- accept_change: {"change_text": "text in the tracked change to accept"}
- scroll_to: {"chunk": chunk_index} (navigate to a different part of the document)
- search_forward: {"query": "text to search for"}

Rules:
- ONE tool call per response, as valid JSON (no markdown fences)
- Use EXACT text from the document for the target parameter
- Fix the most impactful corruption first (highest similarity improvement)
"""


def get_model_action(client: OpenAI, chunk: str, instruction: str, similarity: float, history: List[str]) -> dict:
    history_text = "\n".join(history[-5:]) if history else "No previous actions."
    user_msg = (
        f"Document chunk:\n{chunk}\n\n"
        f"Edit instruction: {instruction}\n\n"
        f"Current similarity: {similarity:.3f}\n"
        f"Recent actions:\n{history_text}\n\n"
        f"Respond with ONE JSON tool call."
    )
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            max_tokens=512,
        )
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return json.loads(text)
    except Exception as exc:
        print(f"[DEBUG] Model error: {exc}", flush=True)
        return {"tool": "replace", "params": {"target": "", "content": ""}}


async def create_env():
    """Create environment client — tries multiple strategies."""
    from doc_edit_game_v2 import DocEditGameV2Env

    # Strategy 1: local Docker image (if explicitly provided)
    if LOCAL_IMAGE_NAME:
        print(f"[DEBUG] Using local Docker image: {LOCAL_IMAGE_NAME}", flush=True)
        return await DocEditGameV2Env.from_docker_image(LOCAL_IMAGE_NAME)

    # Strategy 2: pull from HF Docker registry via from_env
    print(f"[DEBUG] Pulling from HF registry: {HF_REPO_ID}", flush=True)
    return await DocEditGameV2Env.from_env(HF_REPO_ID)


async def run_task(env, task_name: str) -> dict:
    from doc_edit_game_v2 import DocEditAction

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset(task_name=task_name)
        obs = result.observation
        max_steps = obs.steps_remaining

        for step in range(1, max_steps + 1):
            if result.done:
                break

            action_dict = get_model_action(client, obs.document_chunk, obs.edit_instruction, obs.similarity, history)
            action = DocEditAction(
                tool=action_dict.get("tool", "replace"),
                params=action_dict.get("params", {}),
            )

            result = await env.step(action)
            obs = result.observation
            reward = result.reward or 0.0
            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=json.dumps(action_dict), reward=reward, done=result.done)
            history.append(f"Step {step}: {action_dict.get('tool')} success={obs.last_tool_success} sim={obs.similarity:.3f}")

            if result.done:
                break

        score = obs.similarity
        success = score >= SUCCESS_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] Task {task_name} error: {exc}", flush=True)
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return {"task": task_name, "score": score, "success": success, "steps": steps_taken}


async def main():
    env = await create_env()
    results = []

    try:
        for task in TASKS:
            r = await run_task(env, task)
            results.append(r)
            print(f"\n{'='*60}", flush=True)
    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", flush=True)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        print(f"  [{status}] {r['task']}: score={r['score']:.3f} steps={r['steps']}")
    avg = sum(r["score"] for r in results) / len(results) if results else 0
    print(f"  Average score: {avg:.3f}")


if __name__ == "__main__":
    asyncio.run(main())
