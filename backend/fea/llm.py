"""OpenAI-compatible client for open models served on AMD (AMD Token Factory, or a vLLM endpoint on
AMD Developer Cloud). Records latency and token usage of every call for the AMD benchmark panel."""
from __future__ import annotations

import base64
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CallStat:
    task: str
    model: str
    seconds: float
    prompt_tokens: int
    completion_tokens: int

    @property
    def tok_per_s(self) -> float:
        return round(self.completion_tokens / self.seconds, 1) if self.seconds else 0.0


@dataclass
class AMDModel:
    base_url: str = field(default_factory=lambda: os.getenv("AMD_TF_BASE_URL", ""))
    api_key: str = field(default_factory=lambda: os.getenv("AMD_TF_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("AMD_TF_MODEL", ""))
    vision_model: str = field(default_factory=lambda: os.getenv("AMD_TF_VISION_MODEL", "") or os.getenv("AMD_TF_MODEL", ""))
    timeout: float = 120.0
    stats: list[CallStat] = field(default_factory=list)

    @property
    def live(self) -> bool:
        return bool(self.base_url and self.api_key and (self.model or self.vision_model))

    def _client(self):
        from openai import OpenAI
        return OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout, max_retries=2)

    def chat(self, task: str, messages: list[dict], vision: bool = False, temperature: float = 0.0, max_tokens: int = 1500) -> str:
        model = self.vision_model if vision else self.model
        t0 = time.perf_counter()
        r = self._client().chat.completions.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
        dt = time.perf_counter() - t0
        u = getattr(r, "usage", None)
        self.stats.append(CallStat(task, model, round(dt, 3), getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0))
        return r.choices[0].message.content or ""

    def list_models(self) -> list[str]:
        return sorted(m.id for m in self._client().models.list().data)


def image_part(path: Path) -> dict:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(path.read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


def parse_json(text: str) -> dict:
    """Models sometimes wrap JSON in prose or ```json fences; take the outermost object."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("model did not return a JSON object")
    return json.loads(m.group(0))
