"""LLM API 客户端（OpenAI 兼容格式，对接 MiMo）。

职责：
- 封装 HTTP 请求，调用 /chat/completions 接口
- 提供 chat() 返回纯文本，chat_json() 返回解析后的 dict
- API Key / Base URL / Model 支持环境变量和参数传入
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import urllib.request
import urllib.error


def _repair_json_strings(text: str) -> str:
    """Fix unescaped double quotes and bare newlines inside JSON string values.

    LLMs sometimes output strings like: "answer is \"42\"" with unescaped inner quotes.
    We use a character-by-character approach: when inside a string, a '"' is treated
    as closing only if the next non-space char is a JSON delimiter (, } ] : or EOL).
    """
    result: list = []
    in_string = False
    i = 0
    while i < len(text):
        c = text[i]
        if c == '\\' and i + 1 < len(text):
            result.append(c)
            result.append(text[i + 1])
            i += 2
            continue
        if c == '"':
            if not in_string:
                in_string = True
                result.append(c)
            else:
                j = i + 1
                while j < len(text) and text[j] in ' \t':
                    j += 1
                if j >= len(text) or text[j] in ',}]:\n\r':
                    in_string = False
                    result.append(c)
                else:
                    result.append('\\"')
        elif in_string and c == '\n':
            result.append('\\n')
        elif in_string and c == '\r':
            result.append('\\r')
        else:
            result.append(c)
        i += 1
    return ''.join(result)


DEFAULT_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
DEFAULT_MODEL = "mimo-v2.5-pro"
DEFAULT_VISION_MODEL = "mimo-v2.5"


class LLMClient:
    """Minimal OpenAI-compatible chat client using only stdlib."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        vision_model: Optional[str] = None,
        timeout: int = 180,
    ) -> None:
        self.api_key = api_key or os.environ.get("MIMO_API_KEY", "")
        self.base_url = (base_url or os.environ.get("MIMO_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.model = model or os.environ.get("MIMO_MODEL", DEFAULT_MODEL)
        self.vision_model = vision_model or os.environ.get("MIMO_VISION_MODEL", DEFAULT_VISION_MODEL)
        self.timeout = timeout

    def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> str:
        """发送对话请求，返回助手回复的纯文本。

        Args:
            model: 可选，覆盖默认模型。多模态调用时传入 self.vision_model。

        messages 支持多模态格式，content 可为字符串或 list:
          [{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {"url": "data:..."}}]
        """
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format
        if "minimax" in self.base_url.lower():
            payload["reasoning_split"] = True

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        url = f"{self.base_url}/chat/completions"
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM API error {exc.code}: {error_body}") from exc

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"LLM returned no choices: {data}")
        return choices[0]["message"]["content"]

    def chat_json(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Chat and parse the response as JSON."""
        content = self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )
        # Strip markdown code fences if present
        text = content.strip()
        # Strip MiniMax/DeepSeek <think>...</think> blocks
        import re
        text = re.sub(r"<think[^>]*>.*?</think>\s*", "", text, flags=re.DOTALL).strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last fence lines
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        # Fix trailing commas (MiniMax sometimes outputs trailing commas before } or ])
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*\]", "]", text)
        # Fix invalid JSON backslash escapes (LaTeX formulas like \mathcal, \mathbf)
        # Valid JSON escapes: \" \\ \/ \b \f \n \r \t \uXXXX
        # Replace any \X where X is NOT a valid JSON escape char
        # Negative lookbehind: don't fix if already preceded by \ (already escaped)
        text = re.sub(r'(?<!\\)\\([^"\\/bfnrtu])', r'\\\\\1', text)
        # Also fix \u not followed by 4 hex digits (e.g. \url, \usepackage)
        text = re.sub(r'(?<!\\)\\u(?![0-9a-fA-F]{4})', r'\\\\u', text)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            import sys
            # Fallback: repair unescaped double quotes / newlines inside JSON strings
            repaired = _repair_json_strings(text)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass
            # Show context around the error position for debugging
            pos = e.pos if hasattr(e, 'pos') else 0
            start = max(0, pos - 80)
            end = min(len(text), pos + 80)
            print(f"[chat_json] JSON decode failed at pos {pos}:", file=sys.stderr, flush=True)
            print(f"[chat_json] ...{repr(text[start:end])}...", file=sys.stderr, flush=True)
            raise
