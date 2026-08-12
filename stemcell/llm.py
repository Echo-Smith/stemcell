"""LLM 调用封装，支持 OpenAI 兼容协议。"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI


class LLMClient:
    """统一的 LLM 调用客户端。"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        kwargs: dict[str, Any] = {"api_key": config["api_key"]}
        if config.get("base_url"):
            kwargs["base_url"] = config["base_url"]
        self.client = OpenAI(**kwargs)

    def chat(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """单次对话调用，返回文本。"""
        resp = self.client.chat.completions.create(
            model=model or self.config["model"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature if temperature is not None else self.config.get("temperature", 0.7),
            max_tokens=max_tokens or self.config.get("max_tokens", 2048),
            timeout=self.config.get("timeout", 60),
        )
        return resp.choices[0].message.content or ""

    def chat_json(
        self,
        prompt: str,
        system: str = "You are a helpful assistant. Always respond with valid JSON only.",
        model: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """调用并尝试解析为 JSON。"""
        text = self.chat(prompt, system=system, model=model, temperature=temperature)
        # 清理可能的 markdown 代码块包裹
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 兜底：尝试提取第一个 JSON 对象
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start : end + 1])
            raise
