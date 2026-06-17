"""LLM 结构化抽取模块。

调用链（对应手绘图）：
  PDF解析 → text + png
    ├── text+png → Module 1 (结构化抽取) → 类型+按类型分发信息
    └── text    → Module 2 (公式+图解释) → 核心公式 + 对核心图的解释
  → 合并 → 渲染成一个 report

职责：
- Module 1: 结构化抽取（类型判断 + 按类型分发）
- Module 2: 核心公式 + 对图的解释
- 合并两模块结果
- mermaid 子Agent 生成流程图作为 fallback
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, List, Optional

from .llm_client import LLMClient
from .mermaid_agent import build_description_from_paper, generate_mermaid
from .prompt import (
    MODULE1_SYSTEM_PROMPT,
    MODULE2_SYSTEM_PROMPT,
    MODULE2_USER_PROMPT,
    SELECT_VISUAL_SYSTEM_PROMPT,
    SELECT_VISUAL_USER_PROMPT,
)
from .schema import FlowchartBlock, PaperReport


# 长论文截断阈值（字符数），防止超出 LLM 上下文窗口
MAX_INPUT_CHARS = 15000


def _build_multimodal_content(text: str, image_paths: Optional[List[str]] = None) -> Any:
    """构建多模态 user message content。

    如果有图片路径，返回 [text_block, image_block, ...] 列表；
    否则返回纯文本字符串。
    """
    if not image_paths:
        return f"请从以下论文文本中抽取结构化信息：\n\n{text}"

    content: List[Dict[str, Any]] = [
        {"type": "text", "text": f"请从以下论文文本和图片中抽取结构化信息：\n\n{text}"}
    ]
    for img_path in image_paths:
        if not os.path.isfile(img_path):
            continue
        ext = os.path.splitext(img_path)[1].lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"}
        })
    return content


# ============================================================================
# Module 1 — 结构化抽取（类型判断 + 按类型分发）
# ============================================================================


def extract_paper_module1(
    client: LLMClient,
    paper_text: str,
    image_paths: Optional[List[str]] = None,
) -> PaperReport:
    """Module 1: 从论文文本+图片中抽取结构化信息（不含公式）。

    Args:
        client: LLM 客户端
        paper_text: 论文文本
        image_paths: PDF 提取的图片路径列表，与 text 一起作为多模态输入

    流程：
    1. 截断过长文本
    2. 构建多模态消息（text + 图片 base64）
    3. MODULE1_SYSTEM_PROMPT 引导 LLM 输出结构化 JSON
    4. 解析为 PaperReport 对象
    5. _ensure_flowchart 检测并补充缺失的流程图
    """
    truncated = paper_text[:MAX_INPUT_CHARS] if len(paper_text) > MAX_INPUT_CHARS else paper_text
    user_content = _build_multimodal_content(truncated, image_paths)
    messages = [
        {"role": "system", "content": MODULE1_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    # 有图片时用多模态模型 mimo-v2.5，纯文本用默认模型
    use_model = client.vision_model if image_paths else None
    raw = client.chat_json(messages, temperature=0.2, max_tokens=4096, model=use_model)
    report = PaperReport.from_dict(raw)

    # If flowchart/figure is missing, use mermaid sub-agent to generate one
    report = _ensure_flowchart(client, report)
    return report


# ============================================================================
# Module 2 — 核心公式 + 对图的解释
# ============================================================================


def extract_paper_module2(client: LLMClient, paper_text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
    """Module 2: 从论文文本 + 单张核心图中提取公式和对图的解释。

    每次只处理一张图，有多少张核心图就调多少次。

    Args:
        client: LLM 客户端
        paper_text: 论文文本
        image_path: 单张核心图的路径（与 text 一起多模态输入）

    返回:
        {
          "core_formulas": ["LaTeX公式1", ...],
          "figure_explanations": [{"figure_id": ..., "description": ..., "key_components": [...]}, ...]
        }
    """
    truncated = paper_text[:MAX_INPUT_CHARS] if len(paper_text) > MAX_INPUT_CHARS else paper_text

    # 构建多模态消息: text + 单张图片
    if image_path and os.path.isfile(image_path):
        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        user_content: Any = [
            {"type": "text", "text": MODULE2_USER_PROMPT.format(text=truncated)},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]
    else:
        user_content = MODULE2_USER_PROMPT.format(text=truncated)

    messages = [
        {"role": "system", "content": MODULE2_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    # 有图片时用多模态模型 mimo-v2.5
    use_model = client.vision_model if (image_path and os.path.isfile(image_path)) else None
    raw = client.chat_json(messages, temperature=0.2, max_tokens=4096, model=use_model)
    # 确保返回结构合法
    if not isinstance(raw, dict):
        raw = {}
    return {
        "core_formulas": raw.get("core_formulas", []),
        "figure_explanations": raw.get("figure_explanations", []),
    }


def extract_all_module2(
    client: LLMClient,
    paper_text: str,
    image_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """对每张核心图调用一次 Module 2，合并所有结果。

    有 N 张核心图就调 N 次，没有图则只调 1 次（纯文本）。
    公式取所有调用结果的并集（去重），图解释全部收集。
    """
    if not image_paths:
        # 没有图，纯文本调用一次
        return extract_paper_module2(client, paper_text, image_path=None)

    all_formulas: List[str] = []
    all_explanations: List[Dict[str, Any]] = []

    for img_path in image_paths:
        result = extract_paper_module2(client, paper_text, image_path=img_path)
        # 收集公式（去重）
        for f in result.get("core_formulas", []):
            if f and f not in all_formulas:
                all_formulas.append(f)
        # 收集图解释
        all_explanations.extend(result.get("figure_explanations", []))

    return {
        "core_formulas": all_formulas,
        "figure_explanations": all_explanations,
    }


# ============================================================================
# 合并 Module 1 + Module 2 结果
# ============================================================================


def merge_modules(report: PaperReport, module2_result: Dict[str, Any]) -> PaperReport:
    """将 Module 2 的公式和图解释合并到 Module 1 的结构化报告中。"""
    # 合并公式
    formulas = module2_result.get("core_formulas", [])
    if isinstance(formulas, list):
        report.core_formulas = formulas

    # 合并图解释：如果 Module 2 返回了图解释，用于丰富 figure/flowchart 的 explanation
    fig_explanations = module2_result.get("figure_explanations", [])
    if fig_explanations and isinstance(fig_explanations, list):
        # 取第一个图解释作为主解释
        main_explanation = fig_explanations[0]
        desc = main_explanation.get("description", "") if isinstance(main_explanation, dict) else str(main_explanation)
        if desc:
            if report.figure and not report.figure.explanation.strip().startswith("未提及") == False:
                # 如果 figure 已有解释且不是“未提及”，保留原解释
                pass
            elif report.figure:
                report.figure.explanation = desc
            if report.flowchart and report.flowchart.explanation in ("未提及", "基于论文核心方法自动生成的流程图。"):
                report.flowchart.explanation = desc

    return report


# ============================================================================
# 向后兼容: extract_paper = Module1 + Module2 合并
# ============================================================================


def extract_paper(client: LLMClient, paper_text: str, image_paths: Optional[List[str]] = None) -> PaperReport:
    """从论文原文中抽取结构化信息（向后兼容入口，内部调用 Module1+Module2）。"""
    report = extract_paper_module1(client, paper_text, image_paths)
    module2 = extract_all_module2(client, paper_text, image_paths)
    report = merge_modules(report, module2)
    return report


def _ensure_flowchart(client: LLMClient, report: PaperReport) -> PaperReport:
    """为所有非 dataset 类型强制生成 mermaid 流程图。

    规则：
    - model/industrial/analysis/unknown → 始终调用 mermaid 子Agent 生成
    - dataset 类型：不需要流程图

    mermaid 作为主流程图展示，PDF 原图作为补充参考。
    """
    needs_flowchart = report.paper_type in {"model", "industrial", "analysis", "unknown"}

    if not needs_flowchart:
        return report

    # 从报告字段拼装文字描述，作为 mermaid 子Agent 的输入
    description = build_description_from_paper(
        title=report.title,
        core_innovations=report.core_innovations,
        key_methods=report.key_methods,
        main_conclusion=report.main_conclusion,
    )
    # 调用 mermaid 子Agent，最多3轮重试生成有效流程图
    mermaid_code = generate_mermaid(client, description)

    if mermaid_code:
        explanation = report.flowchart.explanation if report.flowchart else "基于论文核心方法自动生成的流程图。"
        flowchart = FlowchartBlock(
            title="核心流程图",
            mermaid=mermaid_code,
            explanation=explanation,
        )
        report.flowchart = flowchart

    return report


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pdf_reader import FigureFile


def select_best_visual(
    client: LLMClient,
    report: PaperReport,
    verified_fig: "FigureFile | None",
) -> PaperReport:
    """对比 mermaid 流程图和 PDF 原图，让 LLM 仲裁选择核心可视化。

    调用时机：mermaid 已生成 + 图片验证后。

    逻辑：
    - 只有 mermaid 没有 PDF 图 → 保留 mermaid
    - 只有 PDF 图没有 mermaid → 保留 PDF 图
    - 两者都有 → 交给 LLM 比较后选择
    - 选择后清除未被选中的那个
    """
    has_mermaid = report.flowchart and report.flowchart.has_mermaid
    has_figure = verified_fig is not None

    if has_mermaid and not has_figure:
        return report
    if has_figure and not has_mermaid:
        return report
    if not has_mermaid and not has_figure:
        return report

    # 两者都有 → LLM 仲裁
    mermaid_code = report.flowchart.mermaid
    innovations_str = "\n".join(f"- {i}" for i in report.core_innovations) if report.core_innovations else "未提及"
    figure_context = f"尺寸: {verified_fig.width}x{verified_fig.height}\n页码: 第{verified_fig.page+1}页\n页面文字: {verified_fig.context[:500]}"

    user_prompt = SELECT_VISUAL_USER_PROMPT.format(
        title=report.title,
        innovations=innovations_str,
        mermaid=mermaid_code,
        figure_info=figure_context,
    )
    messages = [
        {"role": "system", "content": SELECT_VISUAL_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        result = client.chat_json(messages, temperature=0.2, max_tokens=256)
        choice = result.get("choice", "mermaid")
        reason = result.get("reason", "")
    except Exception:
        choice = "mermaid"
        reason = "仲裁异常，默认使用 mermaid"

    if choice == "figure":
        report.flowchart = None
        if report.figure:
            report.figure.explanation = reason
    else:
        report.figure = None
        if report.flowchart:
            report.flowchart.explanation = reason or report.flowchart.explanation

    return report


def extract_papers(client: LLMClient, paper_texts: List[str]) -> List[PaperReport]:
    """批量抽取多篇论文（依次调用 extract_paper）。"""
    reports: List[PaperReport] = []
    for text in paper_texts:
        report = extract_paper(client, text)
        reports.append(report)
    return reports
