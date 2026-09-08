"""Decision comparison and controlled benchmark commands."""

from __future__ import annotations

from pathlib import Path

import click

from .benchmark import load_cases, report_ratings, run_benchmark
from .config import load_env_file
from .llm import CallBudgetExceeded, UsageLedger
from .offline import OfflineClient
from .pipeline import STRATEGIES, Pipeline
from .render import render_comparison


def common_options(function):
    for option in reversed(
        [
            click.option(
                "--config",
                "-c",
                default="config.example.yaml",
                type=click.Path(exists=True, dir_okay=False, path_type=Path),
                help="YAML 配置",
            ),
            click.option(
                "--env-file",
                type=click.Path(exists=True, dir_okay=False, path_type=Path),
                help="读取现有模型配置，不复制密钥",
            ),
            click.option("--offline", is_flag=True, help="协议模拟：不调用模型、不测量效果"),
            click.option(
                "--max-calls",
                type=click.IntRange(1, 10000),
                help="本进程逻辑调用上限（不是费用上限）",
            ),
        ]
    ):
        function = option(function)
    return function


def build_pipeline(config, env_file, offline, max_calls):
    if env_file and not offline:
        load_env_file(env_file)
    values = Pipeline._load_config(config)
    pipe = values.setdefault("pipeline", {})
    if max_calls is not None:
        pipe["max_calls"] = max_calls
    if offline:
        client = OfflineClient(UsageLedger(pipe.get("max_calls", 200)))
        return Pipeline(config=values, llm=client, judge_llm=client)
    return Pipeline(config=values)


def fail(exc):
    # Provider errors may embed request bodies, URLs, headers or secrets.
    # Configuration/schema errors use local fixed messages; provider text is never echoed.
    if isinstance(exc, (ValueError, FileNotFoundError, FileExistsError, CallBudgetExceeded)):
        raise click.ClickException(str(exc)) from None
    raise click.ClickException(
        f"操作失败：{type(exc).__name__}。请核对接口、模型与配置；密钥和响应正文未输出。"
    ) from None


@click.group()
def main():
    """Stemcell：比较方案取舍，验证多视角是否真的有用。"""


@main.command()
@common_options
@click.option(
    "--input",
    "-i",
    "input_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--strategy", type=click.Choice(STRATEGIES), default="stemcell", show_default=True)
@click.option("--count", "-n", type=click.IntRange(1, 12), default=None)
@click.option(
    "--top",
    "-t",
    type=click.IntRange(1, 12),
    default=None,
    help="仅限制 JSON 辅助排序集合，不省调用",
)
@click.option("--perspectives", "-p", default=None, help="逗号分隔的视角；只适用于 Stemcell 方法")
@click.option("--format", "fmt", type=click.Choice(["text", "markdown", "json"]), default="text")
@click.option("--output", "-o", type=click.Path(dir_okay=False, path_type=Path))
def run(
    config,
    env_file,
    offline,
    max_calls,
    input_path,
    strategy,
    count,
    top,
    perspectives,
    fmt,
    output,
):
    """为一个需求输出结构化方案对比。"""
    pipeline, result = None, None
    try:
        pipeline = build_pipeline(config, env_file, offline, max_calls)
        result = pipeline.run(
            input_path.read_text(encoding="utf-8"),
            strategy=strategy,
            count=count,
            top_n=top,
            perspectives=perspectives.split(",") if perspectives is not None else None,
        )
        result["offline"] = offline
        if fmt == "json":
            target = output or Path("output.json")
            pipeline.export_json(result, target)
            click.echo(f"已导出：{target}")
        else:
            body = (
                "离线协议模拟，不代表真实模型效果。\n\n" if offline else ""
            ) + render_comparison(result)
            click.echo(body)
            if output:
                output.write_text(body, encoding="utf-8")
        if result["status"] != "complete":
            click.echo("本次结果不完整，详见候选错误类型和评审状态。", err=True)
            raise click.exceptions.Exit(2)
    except click.exceptions.Exit:
        raise
    except Exception as exc:
        if pipeline is not None and result is None:
            usage = pipeline.ledger.summary()
            click.echo(f"失败前已尝试 {usage['calls']} 次调用；缺失用量不计为零。", err=True)
            target = (
                (output or Path("output.json"))
                if fmt == "json"
                else (output.with_suffix(output.suffix + ".error.json") if output else None)
            )
            if target is not None:
                try:
                    pipeline.export_json(
                        {
                            "status": "failed",
                            "error_type": type(exc).__name__,
                            "offline": offline,
                            "usage": usage,
                        },
                        target,
                    )
                except OSError:
                    click.echo("错误记录无法写入指定输出位置。", err=True)
        fail(exc)


@main.command()
@common_options
@click.option(
    "--cases", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option("--output", "-o", required=True, type=click.Path(file_okay=False, path_type=Path))
@click.option("--limit", type=click.IntRange(1), default=None)
@click.option("--count", type=click.IntRange(1, 12), default=3, show_default=True)
@click.option("--seed", type=int, default=42, show_default=True)
@click.option("--include-no-reset", is_flag=True, help="增加生成阶段不使用摘要的消融组")
def benchmark(
    config, env_file, offline, max_calls, cases, output, limit, count, seed, include_no_reset
):
    """运行三组对照，导出匿名盲评材料与空白评分表。"""
    try:
        pipeline = build_pipeline(config, env_file, offline, max_calls)
        strategies = ("single_prompt", "sampling", "stemcell") + (
            ("stemcell_no_reset",) if include_no_reset else ()
        )
        summary = run_benchmark(
            pipeline,
            load_cases(cases, limit),
            output,
            count=count,
            seed=seed,
            strategies=strategies,
            offline=offline,
            progress=lambda msg: click.echo(msg, err=True),
        )
        click.echo(
            f"报告：{output / 'REPORT.md'}\n盲评：{output / 'blind'}\n人工记录：{output / 'ratings.csv'}"
        )
        if any(c["status"] != "complete" for c in summary["cases"]):
            raise click.exceptions.Exit(2)
    except click.exceptions.Exit:
        raise
    except Exception as exc:
        fail(exc)


@main.command()
@click.option(
    "--experiment", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path)
)
def report(experiment):
    """汇总人工填表，不用模型评分代替用户选择。"""
    try:
        result = report_ratings(experiment)
        click.echo(f"已填写偏好：{result['rated_cases']}；报告：{experiment / 'HUMAN_REPORT.md'}")
    except Exception as exc:
        fail(exc)


@main.command()
def list_perspectives():
    """列出内置路线与兼容视角。"""
    from .modules.clone import PERSPECTIVES

    for name, meta in PERSPECTIVES.items():
        click.echo(f"{name:15s} {meta['label']}")


if __name__ == "__main__":
    main()
