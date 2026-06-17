"""Pipeline 核心编排模块。

调用链（对应手绘图）：
  PDF解析 → text + png
    ├── text+png → Module 1 (结构化抽取) → 类型+按类型分发信息
    └── text    → Module 2 (公式+图解释) → 核心公式 + 对核心图的解释
  → 类型分发 → 核心图验证 → 合并 → 渲染成一个 report

模式：
- 模式1 (--spec):   JSON spec → 解析 → 类型路由 → 校验 → 渲染
- 模式2 (--paper-text): 纯文本 → Module1+Module2 → 类型路由 → 校验 → 渲染
- 模式3 (--pdf):   PDF → 提取文本+图片 → Module1+Module2 → 类型分发 → 图片验证 → 合并 → 渲染
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .extractor import (
    extract_all_module2,
    extract_paper,
    extract_paper_module1,
    extract_paper_module2,
    extract_papers,
    merge_modules,
    select_best_visual,
)
from .figure_verifier import verify_figures
from .llm_client import LLMClient
from .pdf_reader import extract_figures, extract_text
from .renderer import render_report
from .schema import FigureBlock, PaperReport, validate_report
from .type_router import route_paper_type


def generate_report_from_spec(spec_path: str, strict: bool = False) -> Tuple[str, List[str]]:
    """模式1：从预构建的 JSON spec 文件生成报告（不调用 LLM）。"""
    spec = load_json(spec_path)
    raw_papers = spec.get("papers")
    if not isinstance(raw_papers, list):
        raise ValueError("spec must contain a 'papers' list")

    reports: List[PaperReport] = []
    warnings: List[str] = []
    for idx, raw in enumerate(raw_papers, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"papers[{idx}] must be an object")
        report = PaperReport.from_dict(raw)
        report.paper_type = route_paper_type(report)
        errors = validate_report(report)
        if errors:
            message = f"paper {idx} validation warnings: {', '.join(errors)}"
            if strict:
                raise ValueError(message)
            warnings.append(message)
        reports.append(report)

    title = str(spec.get("report_title") or "论文拆解报告")
    return render_report(reports, title=title), warnings


def generate_report_from_text(
    paper_texts: List[str],
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    title: str = "论文拆解报告",
    strict: bool = False,
) -> Tuple[str, List[str]]:
    """模式2：从纯文本输入走 Module1+Module2 抽取，再渲染报告。"""
    client = LLMClient(api_key=api_key, base_url=base_url, model=model)
    reports: List[PaperReport] = []
    warnings: List[str] = []

    for idx, text in enumerate(paper_texts, start=1):
        # Module 1: 结构化抽取
        report = extract_paper_module1(client, text)
        # Module 2: 公式 + 图解释（纯文本模式无图，调 1 次）
        module2 = extract_all_module2(client, text)
        # 合并
        report = merge_modules(report, module2)
        # 类型路由
        report.paper_type = route_paper_type(report)
        errors = validate_report(report)
        if errors:
            message = f"paper {idx} validation warnings: {', '.join(errors)}"
            if strict:
                raise ValueError(message)
            warnings.append(message)
        reports.append(report)

    return render_report(reports, title=title), warnings


def load_json(path: str) -> Dict[str, Any]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("spec root must be an object")
    return data


def generate_report_from_pdf(
    pdf_paths: List[str],
    output_dir: str,
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    title: str = "论文拆解报告",
    strict: bool = False,
) -> Tuple[str, List[str]]:
    """模式3：从 PDF 生成报告。

    流程（对应手绘图）：
    1. PDF解析 → text + png
    2. text+png → Module 1 (结构化抽取: 类型判断 + 按类型分发)
    3. text → Module 2 (公式 + 对图的解释)
    4. 类型分发：
       - model → 架构/创新
       - dataset → 数据 demo
       - analysis → 找核心图 1-3 个
    5. 核心图验证（PDF原图 confidence≥0.6）
    6. 核心图 + 其他信息 → 合并处理成一个 report
    """
    client = LLMClient(api_key=api_key, base_url=base_url, model=model)
    reports: List[PaperReport] = []
    warnings: List[str] = []

    for idx, pdf_path in enumerate(pdf_paths, start=1):
        import sys
        import time as _time
        print(f"[{idx}/{len(pdf_paths)}] 处理: {Path(pdf_path).name}", file=sys.stderr, flush=True)

        # ===== 步骤1: PDF解析 → text + png =====
        t0 = _time.time()
        paper_text = extract_text(pdf_path)
        figures_dir = str(Path(output_dir) / "assets")
        figures = extract_figures(pdf_path, figures_dir, max_figures=3)
        t1 = _time.time()
        print(f"  │ 步骤1 PDF解析: {t1-t0:.1f}s (文本{len(paper_text)}字, {len(figures)}张图)", file=sys.stderr, flush=True)

        # ===== 步骤2: Module 1 — 结构化抽取(类型判断+按类型分发) =====
        # text + png 一起丢给模型（多模态输入）
        # MIMO_NO_VISION=1 时跳过图片传给 LLM（用于不支持视觉的模型如 MiniMax-M3）
        _use_vision = not os.environ.get("MIMO_NO_VISION")
        figure_paths = [fig.path for fig in figures] if (figures and _use_vision) else None
        t2 = _time.time()
        report = extract_paper_module1(client, paper_text, image_paths=figure_paths)
        t3 = _time.time()
        print(f"  │ 步骤2 Module1(结构化): {t3-t2:.1f}s", file=sys.stderr, flush=True)

        # ===== 步骤3: Module 2 — 公式 + 对图的解释 =====
        # text + 核心图，有几张调几次
        t4 = _time.time()
        module2 = extract_all_module2(client, paper_text, image_paths=figure_paths)
        t5 = _time.time()
        n_figs = len(figure_paths) if figure_paths else 0
        print(f"  │ 步骤3 Module2(公式+图解释, {n_figs}张): {t5-t4:.1f}s", file=sys.stderr, flush=True)

        # ===== 步骤4: 类型分发 =====
        report.paper_type = route_paper_type(report)

        # ===== 步骤5+6: 核心图验证 → LLM仲裁 mermaid vs PDF原图 =====
        t6 = _time.time()
        verified_fig = None
        if figures:
            verified_fig = verify_figures(client, figures, paper_title=report.title)

        # 步骤6: 将 PDF 验证通过的原图录入 report.figure
        if verified_fig:
            rel_path = str(Path(verified_fig.path).relative_to(Path(output_dir)))
            if report.paper_type == "model":
                if report.figure is None:
                    report.figure = FigureBlock(
                        label="Figure 1", path=rel_path,
                        caption="核心架构图",
                        explanation="从 PDF 中提取的核心论文图。",
                    )
                else:
                    report.figure.path = rel_path
            else:
                report.figure = FigureBlock(
                    label="Figure 1", path=rel_path,
                    caption="核心流程图",
                    explanation="从 PDF 中提取的核心论文图。",
                )

        # 步骤6.1: mermaid vs PDF → LLM 仲裁选择最佳可视化
        report = select_best_visual(client, report, verified_fig)
        t7 = _time.time()
        print(f"  │ 步骤5+6 图验证+仲裁: {t7-t6:.1f}s", file=sys.stderr, flush=True)

        # ===== 步骤7: 合并 Module1 + Module2 → 最终 report =====
        report = merge_modules(report, module2)

        errors = validate_report(report)
        if errors:
            message = f"paper {idx} validation warnings: {', '.join(errors)}"
            if strict:
                raise ValueError(message)
            warnings.append(message)
        reports.append(report)
        print(f"  └ 总耗时: {_time.time()-t0:.1f}s", file=sys.stderr, flush=True)

    return render_report(reports, title=title), warnings

