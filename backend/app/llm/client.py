"""Minimal client for AICredits' OpenAI-compatible chat completions (https://aicredits.in/docs/api-reference).

One place for auth, timeouts and error messages, shared by the query planner, the LLM judge and the assistant.
"""
import json
import re
from typing import Any

import httpx

from app.core.config import settings


class LLMError(RuntimeError):
    """Raised with a message that is safe to show to the user (never contains the key)."""


def configured() -> bool:
    return bool(settings.aicredits_api_key.strip())


def _raise_for(r: httpx.Response) -> None:
    if r.status_code == 401:
        raise LLMError("AICredits rejected the key (check FNEV_AICREDITS_API_KEY in backend/.env).")
    if r.status_code == 402:
        raise LLMError("AICredits reports insufficient credits: top up your wallet at https://aicredits.in.")
    if r.status_code == 429:
        raise LLMError("AICredits rate limit hit; try again shortly.")
    if r.status_code >= 400:
        detail = ""
        try:
            detail = r.json().get("error", {}).get("message", "")
        except ValueError:
            pass
        raise LLMError(f"AICredits returned an error ({r.status_code}): {detail}".strip())


def chat(
    messages: list[dict[str, Any]], *, model: str | None = None, tools: list[dict] | None = None, max_tokens: int = 600,
    temperature: float = 0.0, timeout: float = 45.0,
) -> dict[str, Any]:
    """One chat completion; returns the assistant message dict ({"content": ..., "tool_calls": [...]})."""
    key = settings.aicredits_api_key.strip()
    if not key:
        raise LLMError("The LLM is not configured: set FNEV_AICREDITS_API_KEY in backend/.env (key from https://aicredits.in).")
    body: dict[str, Any] = {
        "model": model or settings.aicredits_model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature,
    }
    if tools:
        body["tools"] = tools
    try:
        r = httpx.post(
            settings.aicredits_base_url.rstrip("/") + "/chat/completions", json=body,
            headers={"Authorization": f"Bearer {key}"}, timeout=timeout,
        )
    except httpx.HTTPError as exc:
        raise LLMError(f"Could not reach AICredits: {exc}") from exc
    _raise_for(r)
    try:
        return r.json()["choices"][0]["message"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise LLMError("AICredits returned a malformed response.") from exc


def extract_json(text: str) -> Any:
    """Parse the first JSON object/array in a model reply, tolerating code fences and surrounding prose."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.I)
    for opener, closer in (("{", "}"), ("[", "]")):
        i, j = text.find(opener), text.rfind(closer)
        if i != -1 and j > i:
            try:
                return json.loads(text[i : j + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("no JSON found in the model reply")


def chat_json(messages: list[dict[str, Any]], **kw) -> Any:
    """chat() whose reply must be JSON; one repair attempt if it is not."""
    msg = chat(messages, **kw)
    try:
        return extract_json(msg.get("content") or "")
    except ValueError:
        fixed = chat(
            [*messages, {"role": "assistant", "content": msg.get("content") or ""},
             {"role": "user", "content": "That was not valid JSON. Reply again with ONLY the JSON object, no prose."}], **kw,
        )
        try:
            return extract_json(fixed.get("content") or "")
        except ValueError as exc:
            raise LLMError("The model did not return valid JSON.") from exc
