import json
import re

import httpx
from pydantic import ValidationError

from ..auth.security import AuthError
from ..hardware import snapshot
from .schemas import Generated


def fail(code, status=503):
    return AuthError(status, code, "Local draft generation is unavailable.")


class OllamaGenerator:
    def __init__(self, settings, *, hardware=snapshot):
        self.settings, self.hardware = settings, hardware

    def request(self, path, body=None, timeout=5):
        try:
            with httpx.Client(
                base_url=self.settings.ollama_base_url,
                trust_env=False,
                follow_redirects=False,
                timeout=httpx.Timeout(timeout, connect=3),
            ) as client:
                with client.stream("GET" if body is None else "POST", path, json=body) as response:
                    if response.status_code != 200:
                        raise fail("GENERATOR_SERVICE_ERROR")
                    data = bytearray()
                    for part in response.iter_bytes():
                        data.extend(part)
                        if len(data) > 1024 * 1024:
                            raise fail("GENERATOR_RESPONSE_TOO_LARGE")
                    result = json.loads(data)
                    if not isinstance(result, dict):
                        raise fail("GENERATOR_INVALID_OUTPUT", 422)
                    return result
        except httpx.TimeoutException:
            raise fail("GENERATOR_TIMEOUT") from None
        except (httpx.HTTPError, ValueError):
            raise fail("GENERATOR_OFFLINE") from None

    def inspect(self, *, require_memory=True):
        model = self.settings.generator_model
        # Exact token budgeting currently supports the small Qwen2.5 ChatML family.
        if model != "qwen2.5:0.5b-instruct-q4_K_M":
            raise fail("GENERATOR_MODEL_UNSUPPORTED")
        if self.settings.llm_context_tokens > 2048 or self.settings.llm_output_tokens > 512:
            raise fail("GENERATOR_CONTEXT_LIMIT", 422)
        tags = self.request("/api/tags").get("models", [])
        if not isinstance(tags, list):
            raise fail("GENERATOR_INVALID_OUTPUT", 422)
        item = next((m for m in tags if isinstance(m, dict) and m.get("name") == model), None)
        if (
            not item
            or not isinstance(item.get("digest"), str)
            or not re.fullmatch(r"(?:sha256:)?[a-f0-9]{64}", item["digest"])
        ):
            raise fail("GENERATOR_MODEL_MISSING")
        if (
            item.get("remote_host")
            or item.get("remote_model")
            or type(item.get("size")) is not int
            or not 0 < item["size"] <= 500000000
        ):
            raise fail("GENERATOR_MODEL_UNSUPPORTED")
        details = self.request("/api/show", {"model": model})
        if details.get("remote_host") or details.get("remote_model"):
            raise fail("GENERATOR_MODEL_UNSUPPORTED")
        memory = self.hardware()
        required = max(1.5, item["size"] / 2**30 + 1.0)
        if require_memory and memory.get("available_ram_gib", 0) < required:
            raise fail("GENERATOR_LOW_MEMORY", 409)
        return {
            "model": model,
            "digest": item["digest"],
            "model_bytes": item["size"],
            "required_free_ram_gib": round(required, 2),
            "hardware": memory,
        }

    def generate(self, prompt, prompt_tokens, *, schema=Generated, seed=42):
        if type(seed) is not int or not 0 <= seed <= 2147483647:
            raise fail("GENERATOR_INVALID_OUTPUT", 422)
        info = self.inspect()
        body = {
            "model": info["model"],
            "prompt": prompt,
            "raw": True,
            "stream": False,
            "format": schema.model_json_schema(),
            "keep_alive": 0,
            "options": {
                "num_ctx": self.settings.llm_context_tokens,
                "num_predict": self.settings.llm_output_tokens,
                "num_thread": 2,
                "num_gpu": 0,
                "temperature": 0.2,
                "seed": seed,
                "stop": ["<|im_end|>", "<|endoftext|>"],
            },
        }
        try:
            reply = self.request("/api/generate", body, timeout=180)
            if reply.get("done") is not True or reply.get("done_reason") != "stop":
                raise fail("GENERATOR_TRUNCATED", 422)
            measured = reply.get("prompt_eval_count", 0)
            if (
                type(measured) is not int
                or abs(measured - prompt_tokens) > 2
                or measured + self.settings.llm_output_tokens > self.settings.llm_context_tokens
            ):
                raise fail("GENERATOR_CONTEXT_MISMATCH", 422)
            try:
                result = schema.model_validate_json(reply.get("response", ""))
            except (ValidationError, TypeError):
                raise fail("GENERATOR_INVALID_OUTPUT", 422) from None
            metadata = {
                **info,
                "prompt_tokens": measured,
                "eval_count": reply.get("eval_count"),
                "total_duration_ns": reply.get("total_duration"),
                "load_duration_ns": reply.get("load_duration"),
                "eval_duration_ns": reply.get("eval_duration"),
            }
            return result, metadata
        finally:
            # Also request unload on errors. No automatic retry or fallback provider.
            try:
                self.request("/api/generate", {"model": info["model"], "keep_alive": 0}, timeout=5)
            except AuthError:
                pass
