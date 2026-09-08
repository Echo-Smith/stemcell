"""Controlled generation, common review, and explicit accounting."""

from __future__ import annotations

import json
import time
from pathlib import Path

import yaml

from .llm import CallBudgetExceeded, LLMClient, UsageLedger, positive_int
from .modules import CloneModule, DifferentiateModule, QualityModule, ResetModule
from .schema import validate_base

STRATEGIES = ("stemcell", "single_prompt", "sampling", "stemcell_no_reset")


class Pipeline:
    def __init__(
        self,
        config_path: str | Path = "config.yaml",
        *,
        config: dict | None = None,
        llm=None,
        judge_llm=None,
    ):
        self.config = config if config is not None else self._load_config(config_path)
        if not isinstance(self.config, dict) or not isinstance(self.config.get("llm"), dict):
            raise ValueError("Config needs an llm object")
        pipe = self.config.get("pipeline", {})
        self.count = positive_int(pipe.get("default_count", 3), "default_count")
        self.top_n = positive_int(pipe.get("default_top", 3), "default_top")
        self.concurrent = positive_int(pipe.get("max_concurrent", 3), "max_concurrent")
        self.max_input_chars = positive_int(pipe.get("max_input_chars", 30000), "max_input_chars")
        self.ledger = (
            llm.ledger
            if llm is not None
            else UsageLedger(pipe.get("max_calls", 200), self.config.get("pricing"))
        )
        self.llm = llm if llm is not None else LLMClient(self.config["llm"], self.ledger)
        judge_config = self.config.get("judge", {})
        if judge_llm is not None:
            self.judge_llm = judge_llm
        elif judge_config.get("enabled", False):
            # A separate endpoint must never inherit the generator's literal credentials.
            options = {
                k: v
                for k, v in self.config["llm"].items()
                if k
                not in {"api_key", "base_url", "model", "api_key_env", "base_url_env", "model_env"}
            }
            options.update(
                api_key_env="JUDGE_API_KEY", base_url_env="JUDGE_BASE_URL", model_env="JUDGE_MODEL"
            )
            self.judge_llm = LLMClient({**options, **judge_config}, self.ledger, "judge")
        else:
            self.judge_llm = self.llm
        quality_config = dict(self.config.get("quality", {}))
        if "quality_model" not in quality_config and not judge_config.get("enabled", False):
            quality_config["quality_model"] = self.config["llm"].get("quality_model")
        self.reset = ResetModule(self.llm, self.config["llm"])
        self.clone = CloneModule(pipe)
        self.differentiate = DifferentiateModule(self.llm, self.config["llm"])
        self.quality = QualityModule(self.judge_llm, quality_config)

    @staticmethod
    def _load_config(path: str | Path) -> dict:
        with Path(path).open(encoding="utf-8") as handle:
            value = yaml.safe_load(handle)
        if not isinstance(value, dict):
            raise ValueError("Configuration must be a YAML object")
        return value

    def prepare(self, raw_input: str) -> dict:
        if not raw_input.strip() or len(raw_input) > self.max_input_chars:
            raise ValueError("Input is empty or exceeds max_input_chars")
        return self.reset.run(raw_input)

    def run(
        self,
        raw_input: str,
        perspectives: list[str] | None = None,
        count: int | None = None,
        top_n: int | None = None,
        strategy: str = "stemcell",
        *,
        prepared_base: dict | None = None,
    ) -> dict:
        if strategy not in STRATEGIES:
            raise ValueError("Unknown strategy")
        count = self.count if count is None else positive_int(count, "count")
        top_n = self.top_n if top_n is None else positive_int(top_n, "top_n")
        if count > 12:
            raise ValueError("count must be <= 12")
        if perspectives is not None and strategy not in {"stemcell", "stemcell_no_reset"}:
            raise ValueError("perspectives only applies to stemcell arms")
        if not raw_input.strip() or len(raw_input) > self.max_input_chars:
            raise ValueError("Input is empty or exceeds max_input_chars")
        if prepared_base is not None and prepared_base.get("raw_input") != raw_input:
            raise ValueError("Prepared specification belongs to a different input")
        required_calls = (
            (1 if prepared_base is None else 0)
            + (1 if strategy == "single_prompt" else count)
            + count
        )
        if required_calls > self.ledger.max_calls - len(self.ledger.records):
            raise CallBudgetExceeded(f"Run requires up to {required_calls} available calls")
        if strategy in {"stemcell", "stemcell_no_reset"}:
            self.clone.run({}, perspectives=perspectives, count=count)
        started, mark = time.monotonic(), len(self.ledger.records)
        base = (
            self.prepare(raw_input)
            if prepared_base is None
            else validate_base(prepared_base, raw_input)
        )
        recommendation, clones = None, []
        if strategy == "single_prompt":
            candidates, recommendation = self.differentiate.single_prompt(raw_input, count)
        elif strategy == "sampling":
            candidates = self.differentiate.sample(raw_input, count, self.concurrent)
        else:
            clones = self.clone.run(base, perspectives=perspectives, count=count)
            candidates = self.differentiate.run(
                clones,
                self.concurrent,
                raw_input=raw_input if strategy == "stemcell_no_reset" else None,
            )
        seen, unique, duplicates = set(), [], []
        for candidate in candidates:
            if candidate["status"] != "ok":
                continue
            fingerprint = json.dumps(
                {k: v for k, v in candidate["plan"].items() if k != "title"},
                ensure_ascii=False,
                sort_keys=True,
            )
            if fingerprint in seen:
                duplicates.append(candidate["id"])
                continue
            seen.add(fingerprint)
            unique.append(candidate)
        reviewed = self.quality.evaluate(unique, base)
        top = sorted(
            (c for c in reviewed if c["review_status"] == "reviewed"),
            key=lambda c: c["weighted_total"],
            reverse=True,
        )[:top_n]
        warnings = []
        if duplicates:
            warnings.append("完全重复的候选已去除；语义差异仍需人工判断。")
        if clones and len({c["perspective"] for c in clones}) < len(clones):
            warnings.append("候选数量超过视角数量，部分提示被重复采样。")
        if any(c["status"] != "ok" for c in candidates):
            warnings.append("存在生成失败；失败候选未进入对比。")
        complete = len(reviewed) == count and all(
            c["review_status"] != "unassessed" for c in reviewed
        )
        return {
            "schema_version": "0.2",
            "strategy": strategy,
            "status": "complete" if complete else "partial",
            "base": base,
            "clones": clones,
            "candidates": candidates,
            "comparison": reviewed,
            "top": top,
            "baseline_recommendation": recommendation,
            "duplicate_ids": duplicates,
            "warnings": warnings,
            "requested_count": count,
            "usage": self.ledger.summary(mark),
            "seconds": round(time.monotonic() - started, 3),
            "specification_cost": "shared_excluded" if prepared_base is not None else "included",
            "settings": {
                "generator_model": self.llm.model,
                "judge_model": self.quality.config.get("quality_model") or self.judge_llm.model,
                "temperature": self.config["llm"].get("temperature", 0.7),
                "max_tokens_per_candidate": self.config["llm"].get("max_tokens", 2500),
                "generation_concurrency": self.concurrent,
                "judge_concurrency": self.quality.max_concurrent,
                "dimensions": self.quality.dimensions,
            },
        }

    def print_result(self, result: dict) -> None:
        from rich.console import Console

        from .render import render_comparison

        Console().print(render_comparison(result), markup=False, highlight=False)

    def export_json(self, result: dict, output_path: str | Path) -> None:
        Path(output_path).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
