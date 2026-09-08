"""OpenAI-compatible calls with explicit budgets and observable usage."""

from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
from typing import Any

from openai import OpenAI


class CallBudgetExceeded(RuntimeError):
    pass


def positive_int(value: Any, name: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def finite_number(value: Any, name: str, minimum: float = 0) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < minimum
    ):
        raise ValueError(f"{name} must be a finite number >= {minimum}")
    return float(value)


class UsageLedger:
    def __init__(self, max_calls: int = 200, pricing: dict | None = None):
        self.max_calls = positive_int(max_calls, "max_calls")
        self.pricing = pricing or {}
        for rates in self.pricing.values():
            for key in ("input_per_million", "output_per_million"):
                finite_number(rates[key], key)
        self.records: list[dict] = []
        self.lock = threading.Lock()

    def begin(self, stage: str, model: str, provider: str) -> dict:
        with self.lock:
            if len(self.records) >= self.max_calls:
                raise CallBudgetExceeded("Logical call budget exhausted")
            record = {
                "stage": stage,
                "model": model,
                "provider": provider,
                "status": "pending",
                "input_tokens": None,
                "output_tokens": None,
                "cost": None,
            }
            self.records.append(record)
            return record

    def summary(self, start: int = 0) -> dict:
        records = self.records[start:]

        def total(key, group=records):
            values = [r[key] for r in group]
            if any(v is None for v in values):
                return None
            result = sum(values)
            return None if isinstance(result, float) and not math.isfinite(result) else result

        by_stage = {}
        for stage in sorted({r["stage"] for r in records}):
            group = [r for r in records if r["stage"] == stage]
            by_stage[stage] = {
                "calls": len(group),
                "input_tokens": total("input_tokens", group),
                "output_tokens": total("output_tokens", group),
                "estimated_cost": total("cost", group),
            }

        return {
            "calls": len(records),
            "input_tokens": total("input_tokens"),
            "output_tokens": total("output_tokens"),
            "estimated_cost": total("cost"),
            "by_stage": by_stage,
            "cost_note": "User-supplied rates; null means unknown. Cache discounts not included.",
            "records": [dict(r) for r in records],
        }


class LLMClient:
    def __init__(
        self, config: dict[str, Any], ledger: UsageLedger | None = None, provider: str = "generator"
    ):
        self.config = config
        self.model = os.getenv(config.get("model_env", "OPENAI_MODEL")) or config.get("model")
        if not self.model:
            raise ValueError("Missing model: configure model or model_env")
        key = os.getenv(config.get("api_key_env", "OPENAI_API_KEY")) or config.get("api_key")
        if not key or key == "your-api-key-here":
            raise ValueError("Missing API key: configure api_key_env")
        url = os.getenv(config.get("base_url_env", "OPENAI_BASE_URL")) or config.get("base_url")
        timeout = finite_number(config.get("timeout", 60), "timeout", 0.1)
        self.max_tokens = positive_int(config.get("max_tokens", 2500), "max_tokens")
        self.token_parameter = config.get("token_parameter", "max_tokens")
        if self.token_parameter not in {"max_tokens", "max_completion_tokens"}:
            raise ValueError("Invalid token_parameter")
        if config.get("temperature", 0.7) is not None:
            temp = finite_number(config.get("temperature", 0.7), "temperature")
            if temp > 2:
                raise ValueError("temperature must be <= 2")
        self.client = OpenAI(api_key=key, base_url=url or None, timeout=timeout, max_retries=0)
        self.ledger = ledger if ledger is not None else UsageLedger()
        self.provider = provider

    def chat(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stage: str = "generate",
    ) -> str:
        selected = model or self.model
        record = self.ledger.begin(stage, selected, self.provider)
        started = time.monotonic()
        try:
            kwargs = {
                "model": selected,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                self.token_parameter: positive_int(max_tokens or self.max_tokens, "max_tokens"),
            }
            if self.config.get("temperature", 0.7) is not None:
                kwargs["temperature"] = (
                    temperature if temperature is not None else self.config.get("temperature", 0.7)
                )
            record.update(
                prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                system_sha256=hashlib.sha256(system.encode()).hexdigest(),
                output_limit=kwargs[self.token_parameter],
                token_parameter=self.token_parameter,
                temperature=kwargs.get("temperature"),
            )
            response = self.client.chat.completions.create(**kwargs)
            usage = response.usage
            if usage is not None:
                for key, value in (
                    ("input_tokens", usage.prompt_tokens),
                    ("output_tokens", usage.completion_tokens),
                ):
                    record[key] = value if type(value) is int and value >= 0 else None
                rates = self.ledger.pricing.get(f"{self.provider}/{selected}")
                if rates and all(record[k] is not None for k in ("input_tokens", "output_tokens")):
                    record["cost"] = (
                        record["input_tokens"] * rates["input_per_million"]
                        + record["output_tokens"] * rates["output_per_million"]
                    ) / 1_000_000
                    if not math.isfinite(record["cost"]):
                        record["cost"] = None
            record["finish_reason"] = (
                response.choices[0].finish_reason if response.choices else None
            )
            if not response.choices or response.choices[0].finish_reason != "stop":
                raise ValueError("Incomplete or refused completion")
            content = response.choices[0].message.content
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Empty completion")
            record["status"] = "ok"
            return content
        except Exception as exc:
            record["status"] = "error"
            record["error_type"] = type(exc).__name__
            raise
        finally:
            record["seconds"] = round(time.monotonic() - started, 3)

    def chat_json(
        self,
        prompt: str,
        system: str = "Return valid JSON only.",
        model: str | None = None,
        temperature: float | None = None,
        stage: str = "generate",
        max_tokens: int | None = None,
    ) -> dict:
        raw = self.chat(
            prompt,
            system=system,
            model=model,
            temperature=temperature,
            stage=stage,
            max_tokens=max_tokens,
        ).strip()
        if raw.startswith("```") and raw.endswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        def reject_constant(value):
            raise ValueError("Non-finite JSON number")

        result = json.loads(raw, parse_constant=reject_constant)
        if not isinstance(result, dict):
            raise ValueError("Expected a JSON object")
        return result
