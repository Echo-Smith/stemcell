"""命令行入口。"""

from __future__ import annotations

from pathlib import Path

import click

from .pipeline import Pipeline


@click.group()
def main() -> None:
    """stemcell - 重置→克隆→分化→质控 四阶段Agent流水线。"""
    pass


@main.command()
@click.option("--input", "-i", required=True, type=click.Path(exists=True), help="原始输入文件路径")
@click.option("--config", "-c", default="config.yaml", help="配置文件路径")
@click.option("--perspectives", "-p", default=None, help="视角列表，逗号分隔，如 conservative,engineering,creative,risk")
@click.option("--count", "-n", default=None, type=int, help="生成候选数量")
@click.option("--top", "-t", default=None, type=int, help="输出Top-N")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]), help="输出格式")
@click.option("--output", "-o", default=None, help="输出文件路径（json格式时使用）")
def run(input: str, config: str, perspectives: str | None, count: int | None, top: int | None, fmt: str, output: str | None) -> None:
    """运行完整流水线。"""
    p = Pipeline(config_path=config)

    raw = Path(input).read_text(encoding="utf-8")
    persp_list = perspectives.split(",") if perspectives else None

    result = p.run(raw, perspectives=persp_list, count=count, top_n=top)

    if fmt == "json":
        out_path = output or "output.json"
        p.export_json(result, out_path)
    else:
        p.print_result(result)
        if output:
            p.export_json(result, output)


@main.command()
@click.option("--config", "-c", default="config.yaml", help="配置文件路径")
def list_perspectives(config: str) -> None:
    """列出所有可用视角。"""
    from .modules.clone import PERSPECTIVES

    click.echo("可用视角：")
    for key, meta in PERSPECTIVES.items():
        click.echo(f"  {key:15s} - {meta['label']}")


if __name__ == "__main__":
    main()
