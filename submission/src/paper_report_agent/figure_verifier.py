"""PDF 图片验证子Agent。

职责：
- 用 LLM 判断 PDF 提取的图片是否为论文的核心方法/架构/流程图
- 依据图片所在页面的文字上下文、尺寸、页码等信息综合判断
- confidence ≥ 0.6 才采纳，否则丢弃该图片
"""

from __future__ import annotations

from typing import List, Optional

from .llm_client import LLMClient
from .pdf_reader import FigureFile
from .prompt import VERIFY_FIGURE_SYSTEM_PROMPT, VERIFY_FIGURE_USER_PROMPT


def verify_figures(
    client: LLMClient,
    figures: List[FigureFile],
    paper_title: str = "",
) -> Optional[FigureFile]:
    """逐张验证图片，返回第一张通过验证的核心方法图。

    图片已按面积从大到小排序，优先取最大图。
    全部不通过返回 None，上层会 fallback 到 mermaid。
    """
    for fig in figures:
        if _is_method_figure(client, fig, paper_title):
            return fig
    return None


def _is_method_figure(
    client: LLMClient,
    fig: FigureFile,
    paper_title: str,
) -> bool:
    """向 LLM 提交图片上下文，询问是否为核心方法图。

    输入：论文标题 + 图片尺寸 + 页码 + 页面文字前1000字符
    输出：is_method_figure=True 且 confidence≥0.6 则返回 True
    """
    context_info = (
        f"论文标题：{paper_title}\n"
        f"图片尺寸：{fig.width}x{fig.height} 像素\n"
        f"图片所在页码：第 {fig.page + 1} 页\n"
        f"该页面文字内容（前1000字符）：\n{fig.context}"
    )

    messages = [
        {"role": "system", "content": VERIFY_FIGURE_SYSTEM_PROMPT},
        {"role": "user", "content": VERIFY_FIGURE_USER_PROMPT.format(context_info=context_info)},
    ]

    try:
        # 图片验证使用多模态模型 mimo-v2.5
        result = client.chat_json(messages, temperature=0.1, max_tokens=256, model=client.vision_model)
        is_method = result.get("is_method_figure", False)
        confidence = result.get("confidence", 0.0)
        # Accept if model says yes with confidence >= 0.6
        return bool(is_method) and float(confidence) >= 0.6
    except Exception:
        # On failure, be conservative - don't use the figure
        return False
