"""Unified evaluation harness for DocEdit Game V2."""

from __future__ import annotations

import abc
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from training.docedit_training import (
    build_direct_rewrite_messages,
    build_direct_rewrite_prompt,
    extract_document_from_completion,
)


@dataclass
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


@dataclass
class EvalRecord:
    case_id: str
    adapter_name: str
    elapsed_seconds: float
    exact_match: bool
    similarity: float
    edit_accuracy: float
    collateral_damage: float
    composite_score: float
    metadata: dict[str, Any]


class Adapter(abc.ABC):
    """Base interface for all evaluation backends."""

    name: str

    @abc.abstractmethod
    def solve(self, task: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Return edited_document plus adapter-specific metadata."""


class CopySourceAdapter(Adapter):
    name = "copy_source"

    def solve(self, task: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return task["source"], {"strategy": "copy_source"}


class OracleAdapter(Adapter):
    name = "oracle_target"

    def solve(self, task: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return task["target"], {"strategy": "oracle"}


class OpenAIResponsesAdapter(Adapter):
    """Call OpenAI's Responses API for a direct-rewrite baseline."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        max_output_tokens: int = 8_192,
        temperature: float = 0.0,
        timeout_seconds: int = 180,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv(api_key_env, "")
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.name = f"openai_responses:{model}"

        if not self.api_key:
            raise ValueError(
                f"Missing OpenAI API key. Set {api_key_env} or pass --api-key explicitly."
            )

    def solve(self, task: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        payload = {
            "model": self.model,
            "input": build_direct_rewrite_prompt(task),
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
        }
        response = _post_json(
            url="https://api.openai.com/v1/responses",
            payload=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout_seconds=self.timeout_seconds,
        )
        raw_text = _extract_openai_response_text(response)
        edited_document = extract_document_from_completion(raw_text)
        return edited_document, {
            "endpoint": "responses",
            "model": self.model,
            "response_id": response.get("id"),
        }


class OpenAICompatibleChatAdapter(Adapter):
    """Call an OpenAI-compatible chat endpoint, such as vLLM."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str = "EMPTY",
        max_tokens: int = 8_192,
        temperature: float = 0.0,
        timeout_seconds: int = 180,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.name = f"openai_compatible:{model}"

    def solve(self, task: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        payload = {
            "model": self.model,
            "messages": build_direct_rewrite_messages(task),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        response = _post_json(
            url=f"{self.base_url}/v1/chat/completions",
            payload=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout_seconds=self.timeout_seconds,
        )
        choice = response["choices"][0]
        message = choice.get("message", {})
        raw_text = _coerce_message_content(message.get("content", ""))
        edited_document = extract_document_from_completion(raw_text)
        return edited_document, {
            "endpoint": f"{self.base_url}/v1/chat/completions",
            "model": self.model,
            "finish_reason": choice.get("finish_reason"),
        }


class TransformersLocalAdapter(Adapter):
    """Run local Hugging Face generation without a separate serving stack."""

    def __init__(
        self,
        *,
        model: str,
        adapter_path: str = "",
        max_output_tokens: int = 2_048,
        temperature: float = 0.0,
        trust_remote_code: bool = True,
        load_in_4bit: bool = True,
    ) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        self.torch = torch
        self.model_id = model
        self.adapter_path = adapter_path
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self.name = f"transformers_local:{Path(adapter_path).name if adapter_path else model}"

        tokenizer_id = adapter_path or model
        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_id,
            trust_remote_code=trust_remote_code,
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        model_kwargs: dict[str, Any] = {
            "trust_remote_code": trust_remote_code,
            "torch_dtype": torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            "device_map": "auto" if torch.cuda.is_available() else None,
        }
        if load_in_4bit and torch.cuda.is_available():
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
            )

        if adapter_path:
            from peft import AutoPeftModelForCausalLM

            self.model = AutoPeftModelForCausalLM.from_pretrained(
                adapter_path,
                is_trainable=False,
                **model_kwargs,
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(model, **model_kwargs)
        self.model.eval()

    def solve(self, task: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if getattr(self.tokenizer, "chat_template", None):
            prompt = self.tokenizer.apply_chat_template(
                build_direct_rewrite_messages(task),
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            prompt = build_direct_rewrite_prompt(task)

        inputs = self.tokenizer(prompt, return_tensors="pt")
        if self.torch.cuda.is_available():
            inputs = {key: value.to(self.model.device) for key, value in inputs.items()}

        generate_kwargs = {
            **inputs,
            "max_new_tokens": self.max_output_tokens,
            "do_sample": self.temperature > 0,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }
        if self.temperature > 0:
            generate_kwargs["temperature"] = self.temperature

        with self.torch.inference_mode():
            outputs = self.model.generate(**generate_kwargs)

        prompt_length = inputs["input_ids"].shape[1]
        completion_tokens = outputs[0][prompt_length:]
        raw_text = self.tokenizer.decode(completion_tokens, skip_special_tokens=True)
        edited_document = extract_document_from_completion(raw_text)
        return edited_document, {
            "model": self.model_id,
            "adapter_path": self.adapter_path,
            "backend": "transformers_local",
        }


def load_manifest(path: Path) -> list[BenchmarkCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases: list[BenchmarkCase] = []
    for split_name, split_cases in payload["splits"].items():
        for item in split_cases:
            item.setdefault("split", split_name)
            cases.append(BenchmarkCase(**item))
    return cases


def summarize(records: list[EvalRecord]) -> dict[str, Any]:
    if not records:
        return {
            "count": 0,
            "exact_match_rate": 0.0,
            "mean_similarity": 0.0,
            "mean_composite_score": 0.0,
            "mean_edit_accuracy": 0.0,
            "mean_collateral_damage": 0.0,
            "mean_elapsed_seconds": 0.0,
        }

    count = len(records)
    return {
        "count": count,
        "exact_match_rate": sum(1.0 for record in records if record.exact_match) / count,
        "mean_similarity": sum(record.similarity for record in records) / count,
        "mean_composite_score": sum(record.composite_score for record in records) / count,
        "mean_edit_accuracy": sum(record.edit_accuracy for record in records) / count,
        "mean_collateral_damage": sum(record.collateral_damage for record in records) / count,
        "mean_elapsed_seconds": sum(record.elapsed_seconds for record in records) / count,
    }


def evaluate_cases(
    *,
    cases: list[BenchmarkCase],
    adapter: Adapter,
    task_loader,
    task_grader,
) -> list[EvalRecord]:
    records: list[EvalRecord] = []
    for case in cases:
        task = task_loader(case)
        started_at = time.perf_counter()
        edited_document, metadata = adapter.solve(task)
        elapsed = time.perf_counter() - started_at
        score = task_grader(task, edited_document)
        records.append(
            EvalRecord(
                case_id=case.case_id,
                adapter_name=adapter.name,
                elapsed_seconds=elapsed,
                exact_match=score["similarity"] >= 0.999,
                similarity=score["similarity"],
                edit_accuracy=score["edit_accuracy"],
                collateral_damage=score["collateral_damage"],
                composite_score=score["composite_score"],
                metadata=metadata,
            )
        )
    return records


def write_jsonl(path: Path, records: list[EvalRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record)) + "\n")


def _post_json(
    *,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: int,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **headers,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds,
            context=_build_ssl_context(),
        ) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Request to {url} failed with HTTP {exc.code}: {body}") from exc


def _extract_openai_response_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if output_text:
        return output_text

    chunks: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                chunks.append(text)
    return "\n".join(chunks)


def _coerce_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "".join(parts)
    return str(content)


def _build_ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()
