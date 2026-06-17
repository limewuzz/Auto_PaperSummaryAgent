"""Mermaid 流程图生成子Agent。

职责：
- 接收论文方法的文字描述，输出合法的 mermaid flowchart 代码
- 最多3轮重试：第1轮正常生成，第2轮补充语法提示，第3轮最简模式
- 内置语法校验（检测 flowchart 开头、箭头符号、最少行数）
"""

from __future__ import annotations

import re
from typing import Optional

from .llm_client import LLMClient
from .prompt import (
    MERMAID_RETRY_HINT_ROUND2,
    MERMAID_RETRY_HINT_ROUND3,
    MERMAID_SYSTEM_PROMPT,
    MERMAID_USER_PROMPT,
)

MAX_ROUNDS = 3


def generate_mermaid(client: LLMClient, description: str) -> Optional[str]:
    """从文字描述生成 mermaid 流程图。

    最多3轮重试，每轮都会校验语法，校验通过即返回。
    全部失败返回 None（由上层 pipeline 决定是否使用占位文本）。
    """
    for round_num in range(1, MAX_ROUNDS + 1):
        prompt = _build_prompt(description, round_num)
        messages = [
            {"role": "system", "content": MERMAID_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            content = client.chat(messages, temperature=0.4, max_tokens=2048)
            mermaid_code = _clean_mermaid(content)
            if _validate_mermaid(mermaid_code):
                return mermaid_code
        except Exception:
            continue

    return None


def _build_prompt(description: str, round_num: int) -> str:
    """构建用户 prompt。第2/3轮会追加修正提示，引导 LLM 修复语法错误。"""
    base = MERMAID_USER_PROMPT.format(description=description)
    if round_num == 1:
        return base
    elif round_num == 2:
        return f"{base}\n\n{MERMAID_RETRY_HINT_ROUND2}"
    else:
        return f"{base}\n\n{MERMAID_RETRY_HINT_ROUND3}"


def _clean_mermaid(raw: str) -> str:
    """清理 LLM 输出：去掉 think 块、```mermaid ``` 包裹和多余空白。"""
    text = raw.strip()
    # Strip MiniMax/DeepSeek <think>...</think> blocks
    text = re.sub(r"<think[^>]*>.*?</think>\s*", "", text, flags=re.DOTALL).strip()
    # Remove ```mermaid ... ``` wrapper
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def _validate_mermaid(code: str) -> bool:
    """基础语法校验：检查 flowchart 开头 + 含箭头 + 至少3行。"""
    if not code:
        return False
    lines = code.strip().split("\n")
    # Must start with flowchart directive
    first_line = lines[0].strip().lower()
    if not first_line.startswith("flowchart"):
        return False
    # Must have at least one arrow
    if "-->" not in code:
        return False
    # Must have at least 3 lines (directive + 2 connections)
    if len(lines) < 3:
        return False
    return True


def build_description_from_paper(
    title: str,
    core_innovations: list[str],
    key_methods: list[str],
    main_conclusion: str,
) -> str:
    """从报告字段拼装出输入给 mermaid 子Agent 的文字描述。"""
    parts = [f"论文标题：{title}"]
    if core_innovations:
        parts.append("核心创新点：\n" + "\n".join(f"- {i}" for i in core_innovations))
    if key_methods:
        parts.append("关键方法：" + "、".join(key_methods))
    if main_conclusion and main_conclusion != "未提及":
        parts.append(f"主要结论：{main_conclusion}")
    return "\n\n".join(parts)
