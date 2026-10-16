"""Evolus REST client (https://api.evolus.ai/api/v1). The agent hands work to Evolus building blocks:
  - workflows        : run the intake / supplier-follow-up workflow (async, returns an executionId)
  - AI Tools         : translate, anonymize, summarize ... (/ai-tools/{tool}/run)
  - knowledge library: CBAM regulation texts, answers with sources
  - agent chat       : OpenAI-compatible endpoint https://api.evolus.ai/v1 (model = "<applicationId>:<agentId>")
All calls are optional: without EVOLUS_API_KEY the app runs fully and shows Evolus steps as "not connected"."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

import httpx

API = os.getenv("EVOLUS_API_URL", "https://api.evolus.ai/api/v1")
AGENT_API = os.getenv("EVOLUS_AGENT_API_URL", "https://api.evolus.ai/v1")


@dataclass
class Evolus:
    api_key: str = field(default_factory=lambda: os.getenv("EVOLUS_API_KEY", ""))
    app_id: str = field(default_factory=lambda: os.getenv("EVOLUS_APP_ID", ""))
    log: list[dict] = field(default_factory=list)

    @property
    def connected(self) -> bool:
        return bool(self.api_key and self.app_id)

    def _h(self) -> dict:
        return {"X-ApiKey": self.api_key, "X-Application-Id": self.app_id, "Content-Type": "application/json"}

    def _call(self, method: str, path: str, **kw) -> dict:
        t0 = time.perf_counter()
        r = httpx.request(method, f"{API}{path}", headers=self._h(), timeout=60, **kw)
        self.log.append({"call": f"{method} {path}", "status": r.status_code, "seconds": round(time.perf_counter() - t0, 2)})
        r.raise_for_status()
        return r.json() if r.content else {}

    agent_id: str = field(default_factory=lambda: os.getenv("EVOLUS_AGENT_ID", ""))

    @property
    def agent_ready(self) -> bool:
        return self.connected and bool(self.agent_id)

    def ai_tool(self, tool: str, payload: dict) -> dict:
        return self._call("POST", f"/ai-tools/{tool}/run", json=payload)

    def translate(self, text: str, target_language: str) -> str:
        out = self.ai_tool("translate", {"text": text, "options": {"target": target_language}})
        return out.get("output") or out.get("result") or str(out)

    def anonymize(self, text: str) -> str:
        """Evolus AI Tool: replaces names, e-mails, phones, companies with labels before a file leaves the company (GDPR)."""
        out = self.ai_tool("anonymize", {"text": text})
        return out.get("output") or str(out)

    def agent_reply(self, user_text: str) -> str:
        """Evolus agent (runs on the space's own model: Gemma-4-31B-IT on AMD) via the OpenAI-compatible endpoint."""
        t0 = time.perf_counter()
        r = httpx.post(f"{AGENT_API}/chat/completions",
                       headers={"Authorization": f"Bearer {self.api_key}", **self._h()},
                       json={"model": f"{self.app_id}:{self.agent_id}", "messages": [{"role": "user", "content": user_text}]},
                       timeout=180)
        self.log.append({"call": "POST /v1/chat/completions (agent)", "status": r.status_code, "seconds": round(time.perf_counter() - t0, 2)})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def run_workflow(self, workflow_id: str, inputs: dict) -> dict:
        return self._call("POST", f"/workflows/{workflow_id}/execute", json={"inputs": inputs})

    def execution(self, execution_id: str) -> dict:
        return self._call("GET", f"/executions/{execution_id}")
