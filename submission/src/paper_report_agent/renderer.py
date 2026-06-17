"""Markdown 渲染模块。

职责：
- 将 PaperReport 对象渲染为符合演示样式的 Markdown 文本
- 按论文类型分发不同展示块（数据集信息 / 图片 / 流程图）
- 渲染优先级：PDF原图 > mermaid流程图 > 占位文本
"""

from __future__ import annotations

from typing import Iterable, List

from .schema import DatasetInfo, FigureBlock, FlowchartBlock, PaperReport


def render_report(papers: Iterable[PaperReport], title: str = "论文拆解报告") -> str:
    """主渲染入口：将多篇报告渲染为完整 Markdown 文档。"""
    paper_list = list(papers)
    lines: List[str] = [f"# {title}", "", "---", ""]

    for index, paper in enumerate(paper_list, start=1):
        lines.extend(render_single_paper(paper, index))
        lines.extend(["", "---", ""])

    lines.extend(render_summary_table(paper_list))
    return "\n".join(lines).rstrip() + "\n"


def render_single_paper(paper: PaperReport, index: int) -> List[str]:
    """渲染单篇论文：标题 → 作者 → 创新点 → 公式 → 图表块 → 补充信息。"""
    lines: List[str] = [
        f"## 论文 {index}：{paper.title}",
        "",
        f"**作者：** {format_authors(paper.authors)}",
        "",
        "**核心创新点：**",
        render_core_innovations(paper),
        "",
    ]

    # 核心技术/创新详细描述（约200字）
    if paper.technical_summary:
        lines.append("**核心技术描述：**")
        lines.append(paper.technical_summary)
        lines.append("")

    # Core formulas (after innovations, before type-specific block)
    if paper.core_formulas:
        lines.append("**核心公式：**")
        for formula in paper.core_formulas:
            # 用 $$ 块级公式，兼容 \text{}、\begin{pmatrix} 等复杂 LaTeX
            lines.append(f"$$ {formula} $$")
        lines.append("")

    lines.extend(render_type_specific_block(paper))
    lines.extend(["", "**补充：**"])
    lines.extend(render_bullets(paper.supplements))
    return lines


def render_core_innovations(paper: PaperReport) -> str:
    if not paper.core_innovations:
        return "未提及"
    if len(paper.core_innovations) == 1:
        return paper.core_innovations[0]
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(paper.core_innovations, start=1))


def render_type_specific_block(paper: PaperReport) -> List[str]:
    """按类型分发展示块。

    优先级：
    1. mermaid 流程图（始终优先，模型生成的核心方法图）
    2. PDF 原图（作为补充参考）
    3. dataset 类型 → 数据集信息
    """
    if paper.paper_type == "dataset":
        return render_dataset_block(paper.dataset_info)
    # For all non-dataset types: mermaid first, then PDF figure
    if paper.flowchart and paper.flowchart.has_mermaid:
        return render_flowchart_block(paper.flowchart, "核心流程图")
    if paper.figure and paper.figure.has_image:
        return render_figure_block(paper.figure)
    return render_flowchart_block(paper.flowchart, "核心流程图")


def render_dataset_block(info: DatasetInfo | None) -> List[str]:
    info = info or DatasetInfo()
    data_line = (
        f"规模：{info.scale}；来源：{info.source}；任务：{info.tasks}；"
        f"划分：{info.split}；指标：{info.metrics}；License/可用性："
        f"{info.license} / {info.availability}"
    )
    return [
        "**数据集信息：**",
        f"- **数据概况：** {data_line}",
    ]


def render_figure_block(figure: FigureBlock | None) -> List[str]:
    figure = figure or FigureBlock(explanation="未能从输入中定位核心论文图。")
    lines = ["**流程图1：**"]
    if figure.has_image:
        alt = figure.caption or figure.label
        lines.append(f"![{figure.label}: {alt}]({figure.path})")
    else:
        lines.append("未能从输入中可靠抽取原文核心图。")
    lines.append(f"> 解释：{figure.explanation}")
    return lines


def render_flowchart_block(flowchart: FlowchartBlock | None, default_title: str) -> List[str]:
    flowchart = flowchart or FlowchartBlock(
        title=default_title,
        mermaid="flowchart TD\n    A[\"论文输入\"] --> B[\"结构化抽取\"]\n    B --> C[\"报告输出\"]",
        explanation="未能从输入中抽取完整流程，使用最小结构化流程表示。",
    )
    title = flowchart.title or default_title
    lines = [f"**{title}：**"]
    if flowchart.has_mermaid:
        lines.extend(["```mermaid", flowchart.mermaid.strip(), "```"])
    else:
        lines.append("未提及")
    lines.append(f"> 解释：{flowchart.explanation}")
    return lines


def render_bullets(items: List[str]) -> List[str]:
    if not items:
        return ["- 未提及"]
    return [f"- {item}" for item in items]


def render_summary_table(papers: List[PaperReport]) -> List[str]:
    """渲染尾部总结对比表格。"""
    lines = [
        "# 总结",
        "",
        "| 论文 | 核心创新 | 关键方法 | 主要结论 |",
        "|------|---------|---------|---------|",
    ]
    for paper in papers:
        innovation = first_or_default(paper.core_innovations)
        methods = "、".join(paper.key_methods) if paper.key_methods else "未提及"
        conclusion = paper.main_conclusion or "未提及"
        lines.append(
            f"| {escape_table(paper.title)} | {escape_table(innovation)} | "
            f"{escape_table(methods)} | {escape_table(conclusion)} |"
        )
    return lines


def first_or_default(items: List[str]) -> str:
    return items[0] if items else "未提及"


def format_authors(authors: List[str]) -> str:
    if not authors:
        return "未提及"
    return ", ".join(authors)


def escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")
