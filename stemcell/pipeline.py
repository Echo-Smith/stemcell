"""流水线编排：串联 Reset → Clone → Differentiate → Quality。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .llm import LLMClient
from .modules import CloneModule, DifferentiateModule, QualityModule, ResetModule

console = Console()


class Pipeline:
    """四阶段流水线。"""

    def __init__(self, config_path: str | Path = "config.yaml"):
        self.config = self._load_config(config_path)
        self.llm = LLMClient(self.config["llm"])
        self.reset = ResetModule(self.llm, self.config["llm"])
        self.clone = CloneModule(self.config.get("pipeline", {}))
        self.differentiate = DifferentiateModule(self.llm, self.config["llm"])
        self.quality = QualityModule(self.llm, self.config.get("quality", {}))

    @staticmethod
    def _load_config(path: str | Path) -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"配置文件不存在: {p}，请先 cp config.example.yaml config.yaml")
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def run(
        self,
        raw_input: str,
        perspectives: list[str] | None = None,
        count: int | None = None,
        top_n: int | None = None,
    ) -> dict[str, Any]:
        """执行完整流水线。"""
        pipe_config = self.config.get("pipeline", {})
        perspectives = perspectives or pipe_config.get("default_perspectives")
        count = count or pipe_config.get("default_count", 8)
        top_n = top_n or pipe_config.get("default_top", 4)
        max_concurrent = pipe_config.get("max_concurrent", 6)

        # Stage 1: Reset
        console.print(Panel("[bold blue]Stage 1/4: Reset 重置提炼底座", expand=False))
        base = self.reset.run(raw_input)
        console.print(f"  ✓ 底座提炼完成：{base.get('goal', '')[:60]}")

        # Stage 2: Clone
        console.print(Panel("[bold blue]Stage 2/4: Clone 多视角克隆", expand=False))
        clones = self.clone.run(base, perspectives=perspectives, count=count)
        console.print(f"  ✓ 生成 {len(clones)} 个克隆副本，视角：{', '.join(c['perspective_label'] for c in clones)}")

        # Stage 3: Differentiate
        console.print(Panel("[bold blue]Stage 3/4: Differentiate 批量分化生成", expand=False))
        candidates = self.differentiate.run(clones, max_concurrent=max_concurrent)
        ok_count = sum(1 for c in candidates if c["status"] == "ok")
        console.print(f"  ✓ 生成候选 {ok_count}/{len(candidates)} 成功")

        # Stage 4: Quality
        console.print(Panel("[bold blue]Stage 4/4: Quality 质控打分排序", expand=False))
        scored = self.quality.run(candidates, base, top_n=top_n)
        console.print(f"  ✓ 打分完成，输出 Top {len(scored)}")

        return {
            "base": base,
            "clones": clones,
            "candidates": candidates,
            "top": scored,
        }

    def print_result(self, result: dict[str, Any]) -> None:
        """美化输出结果。"""
        console.print("\n[bold green]══════════ 最终结果 ══════════[/bold green]\n")

        # 打分表
        table = Table(title="候选方案打分排名")
        table.add_column("排名", style="cyan", width=6)
        table.add_column("视角", style="magenta", width=12)
        table.add_column("加权总分", style="yellow", width=10)
        for d in self.quality.dimensions:
            table.add_column(d["label"], width=8)
        table.add_column("点评", style="white")

        for idx, c in enumerate(result["top"], 1):
            scores = c.get("scores", {})
            row = [
                str(idx),
                c["perspective_label"],
                str(c.get("weighted_total", 0)),
            ]
            for d in self.quality.dimensions:
                row.append(str(scores.get(d["name"], "-")))
            row.append(c.get("comment", "")[:40])
            table.add_row(*row)

        console.print(table)
        console.print()

        # Top1 详情
        if result["top"]:
            top1 = result["top"][0]
            console.print(Panel(top1["content"], title=f"🏆 Top 1 - {top1['perspective_label']}（{top1['weighted_total']}分）", border_style="green"))

    def export_json(self, result: dict[str, Any], output_path: str | Path) -> None:
        """导出为 JSON。"""
        Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[green]✓ 已导出到 {output_path}[/green]")
