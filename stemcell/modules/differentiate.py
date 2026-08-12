"""Differentiate 分化模块：每份克隆副本独立生成候选方案。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from ..llm import LLMClient
from .clone import CloneModule

PROMPT_TEMPLATE = """基于以下任务底座和指定视角，生成一份完整的候选方案。

要求：
1. 严格遵循视角指令的倾向
2. 方案要具体、可执行，不要空泛
3. 结构清晰，分点阐述
4. 不要输出JSON，直接输出方案文本

{context}

请输出你的候选方案：
"""


class DifferentiateModule:
    """分化模块：批量生成候选。"""

    def __init__(self, llm: LLMClient, config: dict[str, Any] | None = None):
        self.llm = llm
        self.config = config or {}

    def run_single(self, clone: dict[str, Any]) -> dict[str, Any]:
        """对单个克隆副本生成候选。"""
        context = CloneModule.format_clone_context(clone)
        prompt = PROMPT_TEMPLATE.format(context=context)
        try:
            content = self.llm.chat(
                prompt,
                system="你是一个专业的方案生成助手，根据指定视角输出高质量候选方案。",
                temperature=self.config.get("temperature", 0.8),
            )
            status = "ok"
        except Exception as e:
            content = f"[生成失败] {e}"
            status = "error"

        return {
            "id": clone["id"],
            "perspective": clone["perspective"],
            "perspective_label": clone["perspective_label"],
            "content": content,
            "status": status,
        }

    def run(self, clones: list[dict[str, Any]], max_concurrent: int = 6) -> list[dict[str, Any]]:
        """批量并行生成候选。"""
        results: list[dict[str, Any]] = []
        max_workers = min(max_concurrent, len(clones))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(self.run_single, c): c for c in clones}
            for future in as_completed(future_map):
                results.append(future.result())

        # 按 id 排序，保证输出顺序稳定
        results.sort(key=lambda x: x["id"])
        return results
