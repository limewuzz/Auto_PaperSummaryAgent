"""Heuristic paper type routing."""

from __future__ import annotations

from typing import Iterable

from .schema import PaperReport, PaperType


DATASET_TERMS = (
    "dataset",
    "benchmark",
    "corpus",
    "数据集",
    "基准",
    "语料",
    "annotation",
    "标注",
)

MODEL_TERMS = (
    "architecture",
    "model",
    "framework",
    "method",
    "training",
    "模型",
    "架构",
    "方法",
    "训练",
)

INDUSTRIAL_TERMS = (
    "system",
    "production",
    "serving",
    "deployment",
    "pipeline",
    "inference service",
    "系统",
    "工业",
    "部署",
    "服务",
    "吞吐",
    "延迟",
)

ANALYSIS_TERMS = (
    "analysis",
    "evaluation",
    "study",
    "survey",
    "theory",
    "评测",
    "分析",
    "理论",
    "研究",
)


def route_paper_type(report: PaperReport) -> PaperType:
    """Use explicit type when present; otherwise infer from report text."""
    if report.paper_type != "unknown":
        return report.paper_type

    text = " ".join(
        [
            report.title,
            " ".join(report.core_innovations),
            " ".join(report.key_methods),
            report.main_conclusion,
            " ".join(report.supplements),
        ]
    ).lower()

    scores = {
        "dataset": count_terms(text, DATASET_TERMS),
        "industrial": count_terms(text, INDUSTRIAL_TERMS),
        "model": count_terms(text, MODEL_TERMS),
        "analysis": count_terms(text, ANALYSIS_TERMS),
    }
    best_type = max(scores, key=scores.get)
    if scores[best_type] == 0:
        return "analysis"
    return best_type  # type: ignore[return-value]


def count_terms(text: str, terms: Iterable[str]) -> int:
    return sum(1 for term in terms if term.lower() in text)

