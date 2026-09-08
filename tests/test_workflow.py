import csv
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from stemcell.benchmark import load_cases, report_ratings, run_benchmark
from stemcell.cli import main
from stemcell.config import load_env_file
from stemcell.llm import UsageLedger
from stemcell.offline import OfflineClient
from stemcell.pipeline import Pipeline

CONFIG = Path(__file__).resolve().parents[1] / "config.example.yaml"
RAW = "为个人笔记工具增加导出。\n硬约束：必须离线。\n硬约束：不得修改原文件。"


def pipeline(max_calls=200):
    client = OfflineClient(UsageLedger(max_calls))
    return Pipeline(
        config={"llm": {}, "pipeline": {"max_calls": max_calls}}, llm=client, judge_llm=client
    )


def cases():
    return [
        {
            "id": "case-1",
            "title": "Test",
            "kind": "synthetic",
            "source": "test fixture",
            "input": RAW,
        }
    ]


@pytest.mark.parametrize(
    "strategy,calls",
    [("stemcell", 7), ("sampling", 7), ("single_prompt", 5), ("stemcell_no_reset", 7)],
)
def test_strategy_counts_and_comparison(strategy, calls):
    p = pipeline()
    result = p.run(RAW, strategy=strategy)
    assert result["status"] == "complete"
    assert len(result["comparison"]) == 3
    assert result["top"] == []  # Simulator never supplies verified evidence.
    assert result["usage"]["calls"] == calls
    assert result["usage"]["input_tokens"] is None
    assert result["base"]["raw_input"] == RAW


def test_shared_base_judge_input_and_ablation():
    p = pipeline()
    base = p.prepare(RAW)
    p.llm.chat_json = Mock(wraps=p.llm.chat_json)
    for strategy in ["single_prompt", "sampling", "stemcell", "stemcell_no_reset"]:
        p.run(RAW, strategy=strategy, prepared_base=base)
    calls = p.llm.chat_json.call_args_list
    judge_bases = {
        c.args[0].split("\n完整任务（含原文）：", 1)[1].split("\n候选正文：", 1)[0]
        for c in calls
        if c.kwargs["stage"] == "judge"
    }
    assert len(judge_bases) == 1
    generations = [c.args[0] for c in calls if c.kwargs["stage"] == "generate"]
    assert RAW in generations[0]  # Single prompt gets original material.
    assert any("【任务底座】" in prompt for prompt in generations)
    assert any("路线倾向：" in prompt and RAW in prompt for prompt in generations)
    assert not any(c.kwargs["stage"] == "reset" for c in calls)


def test_budget_preflight_before_any_api_or_files(tmp_path):
    p = pipeline(16)
    with pytest.raises(ValueError, match="17 calls"):
        run_benchmark(p, cases(), tmp_path / "experiment")
    assert not p.ledger.records
    assert not (tmp_path / "experiment").exists()


def test_benchmark_blinding_and_empty_human_report(tmp_path):
    output = tmp_path / "experiment"
    result = run_benchmark(pipeline(), cases(), output, offline=True)
    assert result["usage"]["calls"] == 17
    mapping = json.loads((output / "private/mapping.json").read_text())
    assert set(mapping["case-1"].values()) == {"single_prompt", "sampling", "stemcell"}
    pack = (output / "blind/case-1.md").read_text()
    assert all(
        label not in pack
        for label in ["single_prompt", "sampling", "stemcell", "weighted_total", "最快验证"]
    )
    assert "模拟" in pack
    assert report_ratings(output)["rated_cases"] == 0
    assert "尚无人工偏好" in (output / "HUMAN_REPORT.md").read_text()


def test_preferences_map_correctly_and_reject_offline_quality_claims(tmp_path):
    output = tmp_path / "experiment"
    run_benchmark(pipeline(), cases(), output, offline=True)
    ratings = output / "ratings.csv"
    with ratings.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames, list(reader)
    rows[0].update(preferred_bundle="A", reading_seconds="12")
    with ratings.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="Offline"):
        report_ratings(output)
    # Test report interpretation only, not a real experiment.
    summary_path = output / "private/summary.json"
    summary = json.loads(summary_path.read_text())
    summary["offline"] = False
    summary_path.write_text(json.dumps(summary))
    result = report_ratings(output)
    mapping = json.loads((output / "private/mapping.json").read_text())
    assert result["preferences"] == {mapping["case-1"]["A"]: 1}
    assert result["mean_total_reading_seconds"] == 12


def test_configuration_wires_legacy_judge_model():
    client = OfflineClient()
    p = Pipeline(config={"llm": {"quality_model": "judge-special"}}, llm=client)
    assert p.quality.config["quality_model"] == "judge-special"


@pytest.mark.parametrize("count", [0, -1, 13, True])
def test_invalid_count_does_not_call_model(count):
    p = pipeline()
    with pytest.raises(ValueError):
        p.run(RAW, count=count)
    assert not p.ledger.records


def test_env_file_is_not_executed_or_unrelated_keys_loaded(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('OPENAI_API_KEY="test-only"\nOPENAI_MODEL=model\nLANGFUSE_SECRET_KEY=ignore\n')
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    load_env_file(env)
    import os

    assert os.environ["OPENAI_API_KEY"] == "test-only"
    assert "LANGFUSE_SECRET_KEY" not in os.environ
    env.write_text("OPENAI_API_KEY=$(touch unwanted)\n")
    with pytest.raises(ValueError):
        load_env_file(env)
    assert not (tmp_path / "unwanted").exists()


def test_cli_offline_run_and_benchmark(tmp_path):
    raw = tmp_path / "input.md"
    raw.write_text(RAW)
    out = tmp_path / "comparison.md"
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["run", "--offline", "--config", str(CONFIG), "--input", str(raw), "--output", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert "适用条件" in out.read_text()
    assert "离线协议模拟" in out.read_text()
    manifest = tmp_path / "cases.json"
    manifest.write_text(json.dumps(cases()))
    result = runner.invoke(
        main,
        [
            "benchmark",
            "--offline",
            "--config",
            str(CONFIG),
            "--cases",
            str(manifest),
            "--output",
            str(tmp_path / "bench"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "bench/REPORT.md").exists()


def test_manifest_prevents_path_traversal_and_missing_sources(tmp_path):
    path = tmp_path / "cases.json"
    value = cases()
    value[0]["id"] = "../../bad"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        load_cases(path)


def test_run_budget_preflight_does_not_spend():
    from stemcell.llm import CallBudgetExceeded

    p = pipeline(6)
    with pytest.raises(CallBudgetExceeded):
        p.run(RAW)
    assert not p.ledger.records


def test_failed_cli_run_preserves_usage_without_provider_text(tmp_path, monkeypatch):
    from stemcell import cli

    p = pipeline()

    def failure(raw):
        record = p.ledger.begin("reset", "fake-model", "test")
        record.update(status="error", seconds=0)
        raise RuntimeError("SECRET_PROVIDER_BODY")

    p.prepare = failure
    monkeypatch.setattr(cli, "build_pipeline", lambda *args: p)
    raw, out = tmp_path / "input.md", tmp_path / "failure.json"
    raw.write_text(RAW)
    result = CliRunner().invoke(
        main,
        [
            "run",
            "--config",
            str(CONFIG),
            "--input",
            str(raw),
            "--format",
            "json",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 1
    saved = json.loads(out.read_text())
    assert saved["usage"]["calls"] == 1
    assert saved["usage"]["input_tokens"] is None
    assert "SECRET_PROVIDER_BODY" not in result.output + out.read_text()


def test_exact_duplicate_not_presented_as_extra_route():
    p = pipeline()
    original = p.differentiate.run

    def duplicate(*args, **kwargs):
        generated = original(*args, **kwargs)
        generated[1] = {**generated[0], "id": "clone_01"}
        return generated

    p.differentiate.run = duplicate
    result = p.run(RAW)
    assert result["duplicate_ids"] == ["clone_01"]
    assert len(result["comparison"]) == 2
    assert result["status"] == "partial"
    assert result["usage"]["calls"] == 6


def test_prepared_base_cannot_be_reused_for_different_input():
    p = pipeline()
    base = p.prepare(RAW)
    before = len(p.ledger.records)
    with pytest.raises(ValueError, match="different input"):
        p.run(RAW + "A new requirement.", prepared_base=base)
    assert len(p.ledger.records) == before


def test_separate_judge_does_not_inherit_generator_secrets(monkeypatch):
    import stemcell.pipeline as module

    configs = []

    def client(config, ledger, provider="generator"):
        configs.append((provider, config))
        return OfflineClient(ledger)

    monkeypatch.setattr(module, "LLMClient", client)
    module.Pipeline(
        config={
            "llm": {
                "api_key": "generator-only",
                "base_url": "https://generator.invalid",
                "model": "gen",
            },
            "judge": {"enabled": True},
        }
    )
    judge = configs[1][1]
    assert "api_key" not in judge and "base_url" not in judge and "model" not in judge
    assert judge["api_key_env"] == "JUDGE_API_KEY"


def test_provider_rejection_stops_batch_without_retrying_other_cases(tmp_path):
    class RateLimitError(Exception):
        """Only the error classification is under test."""

    p = pipeline()

    def rejected(raw):
        raise RateLimitError("test")

    p.prepare = rejected
    two = cases() + [{**cases()[0], "id": "case-2"}]
    out = tmp_path / "stopped"
    summary = run_benchmark(p, two, out)
    assert len(summary["cases"]) == 1
    assert summary["stopped_reason"] == "RateLimitError"
    assert report_ratings(out)["rated_cases"] == 0
