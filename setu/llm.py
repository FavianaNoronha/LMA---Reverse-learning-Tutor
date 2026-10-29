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


class DemoLLM(MockLLM):
    """For the demo app only: every third draft is a 'leaky' one (uses words the learner has not met and explains),
    so the leak filter's rejections are visible. Otherwise it echoes the reference sentence."""
    model = "demo-mock"

    def __init__(self):
        super().__init__()
        self.respond = lambda m: (json.dumps({"sentence": "ఇది పుస్తకం ఎందుకంటే నియమం ప్రకారం"}, ensure_ascii=False)
                                  if self.calls % 3 == 1 else json.dumps({"sentence": _ref(m)}, ensure_ascii=False))


def _ref(messages: list[dict]) -> str:
    m = re.search(r"Reference sentence[^:]*:\s*(.+)", next((x["content"] for x in messages if "Reference sentence" in x["content"]), ""))
    return m.group(1).strip() if m else ""


def parse_json(text: str):
    """First JSON object in a model reply, or None."""
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


class AgentMockLLM(MockLLM):
    """Mock that speaks the tool-call protocol of setu.agent. With leaky_every=3, every third conversation starts with a
    leaky draft, so the tool's rejection and the model's revision are visible; otherwise it writes the reference sentence."""
    model = "agent-mock"

    def __init__(self, leaky_every: int = 0, first_draft=None):
        super().__init__()
        self.leaky_every, self.convs, self.first_draft = leaky_every, 0, first_draft

    def chat(self, messages, temperature=0.8, max_tokens=120, schema=None) -> str:
        self.calls += 1
        user = messages[1]["content"]
        iid = re.search(r"Item id: (\S+)", user).group(1)
        if not any(m["content"].startswith("TOOL RESULT") for m in messages):
            self.convs += 1
            leaky = self.first_draft if self.first_draft is not None else (
                "ఇది పుస్తకం ఎందుకంటే నియమం ప్రకారం" if self.leaky_every and self.convs % self.leaky_every == 0 else None)
            sentence = leaky or _ref(messages)
        else:
            sentence = _ref(messages)
        return json.dumps({"tool": "check_classmate_sentence", "args": {"item_id": iid, "sentence": sentence}}, ensure_ascii=False)


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
