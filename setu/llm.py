"""Model access. Any OpenAI-compatible server works: Ollama on a Mac (http://localhost:11434/v1),
vLLM on a GPU box (http://HOST:8000/v1). MockLLM is for tests and offline demos."""
from __future__ import annotations
import json, re, urllib.request
from typing import Callable, Protocol


class LLM(Protocol):
    model: str
    def chat(self, messages: list[dict], temperature: float = 0.8, max_tokens: int = 120,
             schema: dict | None = None) -> str: ...


class OpenAICompatLLM:
    def __init__(self, base_url: str, model: str, timeout: int = 120):
        self.base_url, self.model, self.timeout = base_url.rstrip("/"), model, timeout

    def chat(self, messages, temperature=0.8, max_tokens=120, schema=None) -> str:
        body = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        if schema:  # guided JSON on vLLM / recent Ollama; servers that ignore it still return text we can parse
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "out", "schema": schema}}
        req = urllib.request.Request(self.base_url + "/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.load(r)["choices"][0]["message"]["content"]


class MockLLM:
    """Returns respond(messages) for every call; default echoes the reference sentence in the prompt."""
    model = "mock"

    def __init__(self, respond: Callable[[list[dict]], str] | None = None):
        self.respond = respond or (lambda m: json.dumps({"sentence": _ref(m)}, ensure_ascii=False))
        self.calls = 0

    def chat(self, messages, temperature=0.8, max_tokens=120, schema=None) -> str:
        self.calls += 1
        return self.respond(messages)


def _ref(messages: list[dict]) -> str:
    m = re.search(r"Reference sentence[^:]*:\s*(.+)", messages[-1]["content"])
    return m.group(1).strip() if m else ""


def parse_sentence(text: str) -> str:
    """Pull {"sentence": ...} out of a model reply; fall back to the first non-empty line."""
    try:
        return str(json.loads(text)["sentence"]).strip()
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return str(json.loads(m.group(0))["sentence"]).strip()
            except Exception:
                pass
    lines = [l.strip().strip('"') for l in text.splitlines() if l.strip()]
    return lines[0] if lines else ""
