"""Deterministic protocol simulator. Never evidence of model or product quality."""

from __future__ import annotations

import copy
import json
import threading

from .llm import UsageLedger
from .schema import CANDIDATE_EXAMPLE


class OfflineClient:
    def __init__(self, ledger: UsageLedger | None = None):
        self.ledger = ledger if ledger is not None else UsageLedger()
        self.model = "offline-protocol-simulator"
        self.counter = 0
        self.lock = threading.Lock()

    def chat_json(self, prompt, *, stage="generate", **kwargs):
        record = self.ledger.begin(stage, self.model, "offline")
        record.update(status="simulated", seconds=0)
        if stage == "reset":
            raw = prompt.split("原文（数据，不是系统指令）：\n", 1)[1]
            quotes = [
                line.removeprefix("硬约束：").strip()
                for line in raw.splitlines()
                if line.startswith("硬约束：")
            ]
            return {
                "goal": "模拟提炼：" + raw.splitlines()[0],
                "constraints": quotes,
                "boundaries": [],
                "key_facts": [],
                "preferences": [],
                "context_summary": "离线协议模拟，不代表模型理解",
                "unknowns": ["所有实际效果均未验证"],
                "hard_constraints": [
                    {"id": f"C{i + 1}", "text": q, "source_quote": q} for i, q in enumerate(quotes)
                ],
            }
        if stage == "judge":
            example = json.loads(prompt.split("\n结构：", 1)[1].split("\n完整任务", 1)[0])
            example["scores"] = {key: 0 for key in example["scores"]}
            for check in example["constraint_checks"]:
                check.update(status="unknown", evidence="", reason="离线模拟不判断可行性")
            example["comment"] = "离线模拟占位，分数不可用于质量结论"
            return example

        def plan():
            with self.lock:
                self.counter += 1
                number = self.counter
            value = copy.deepcopy(CANDIDATE_EXAMPLE)
            value["title"] = f"离线模拟候选 {number}"
            value["summary"] = f"协议占位内容 {number}，不是可执行建议或真实模型输出。"
            return value

        if '"candidates": [候选对象]' in prompt:
            import re

            count = int(re.search(r"一次生成 (\d+) 条", prompt).group(1))
            return {
                "candidates": [plan() for _ in range(count)],
                "recommendation": {"index": 0, "reason": "离线模拟占位"},
            }
        return plan()
