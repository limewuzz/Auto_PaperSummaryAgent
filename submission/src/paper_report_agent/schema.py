"""Data structures for demo-aligned paper reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Literal, Optional


PaperType = Literal["dataset", "model", "industrial", "analysis", "unknown"]


@dataclass
class DatasetInfo:
    scale: str = "未提及"
    source: str = "未提及"
    tasks: str = "未提及"
    split: str = "未提及"
    metrics: str = "未提及"
    license: str = "未提及"
    availability: str = "未提及"

    @classmethod
    def from_dict(cls, raw: Optional[Dict[str, Any]]) -> "DatasetInfo":
        raw = raw or {}
        return cls(
            scale=str(raw.get("scale") or "未提及"),
            source=str(raw.get("source") or "未提及"),
            tasks=str(raw.get("tasks") or "未提及"),
            split=str(raw.get("split") or "未提及"),
            metrics=str(raw.get("metrics") or "未提及"),
            license=str(raw.get("license") or "未提及"),
            availability=str(raw.get("availability") or "未提及"),
        )


@dataclass
class FigureBlock:
    label: str = "Figure"
    path: str = ""
    caption: str = ""
    explanation: str = "未提及"

    @classmethod
    def from_dict(cls, raw: Optional[Dict[str, Any]]) -> "FigureBlock":
        raw = raw or {}
        return cls(
            label=str(raw.get("label") or "Figure"),
            path=str(raw.get("path") or ""),
            caption=str(raw.get("caption") or ""),
            explanation=str(raw.get("explanation") or "未提及"),
        )

    @property
    def has_image(self) -> bool:
        return bool(self.path.strip())


@dataclass
class FlowchartBlock:
    title: str = "流程图1"
    mermaid: str = ""
    explanation: str = "未提及"

    @classmethod
    def from_dict(cls, raw: Optional[Dict[str, Any]]) -> "FlowchartBlock":
        raw = raw or {}
        return cls(
            title=str(raw.get("title") or "流程图1"),
            mermaid=str(raw.get("mermaid") or ""),
            explanation=str(raw.get("explanation") or "未提及"),
        )

    @property
    def has_mermaid(self) -> bool:
        return bool(self.mermaid.strip())


@dataclass
class Evidence:
    claim: str
    source: str = "未提及"
    quote: str = ""

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Evidence":
        return cls(
            claim=str(raw.get("claim") or ""),
            source=str(raw.get("source") or "未提及"),
            quote=str(raw.get("quote") or ""),
        )


@dataclass
class PaperReport:
    title: str
    authors: List[str]
    paper_type: PaperType = "unknown"
    core_innovations: List[str] = field(default_factory=list)
    technical_summary: str = ""  # 200字左右的核心技术/创新描述
    key_methods: List[str] = field(default_factory=list)
    main_conclusion: str = "未提及"
    dataset_info: Optional[DatasetInfo] = None
    figure: Optional[FigureBlock] = None
    flowchart: Optional[FlowchartBlock] = None
    supplements: List[str] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    core_formulas: List[str] = field(default_factory=list)  # LaTeX formulas

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "PaperReport":
        authors = normalize_string_list(raw.get("authors"))
        paper_type = normalize_paper_type(raw.get("paper_type"))
        return cls(
            title=str(raw.get("title") or "未命名论文"),
            authors=authors or ["未提及"],
            paper_type=paper_type,
            core_innovations=normalize_string_list(raw.get("core_innovations")),
            technical_summary=str(raw.get("technical_summary") or ""),
            key_methods=normalize_string_list(raw.get("key_methods")),
            main_conclusion=str(raw.get("main_conclusion") or "未提及"),
            dataset_info=DatasetInfo.from_dict(raw.get("dataset_info"))
            if raw.get("dataset_info") is not None
            else None,
            figure=FigureBlock.from_dict(raw.get("figure"))
            if raw.get("figure") is not None
            else None,
            flowchart=FlowchartBlock.from_dict(raw.get("flowchart"))
            if raw.get("flowchart") is not None
            else None,
            supplements=normalize_string_list(raw.get("supplements")),
            evidence=[
                Evidence.from_dict(item)
                for item in raw.get("evidence", [])
                if isinstance(item, dict)
            ],
            core_formulas=normalize_string_list(raw.get("core_formulas")),
        )


def normalize_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, Iterable):
        result = []
        for item in value:
            text = str(item).strip()
            if text:
                result.append(text)
        return result
    return [str(value)]


def normalize_paper_type(value: Any) -> PaperType:
    text = str(value or "unknown").strip().lower()
    aliases = {
        "data": "dataset",
        "dataset": "dataset",
        "数据集": "dataset",
        "model": "model",
        "method": "model",
        "模型": "model",
        "方法": "model",
        "industrial": "industrial",
        "system": "industrial",
        "系统": "industrial",
        "工业": "industrial",
        "analysis": "analysis",
        "evaluation": "analysis",
        "theory": "analysis",
        "评测": "analysis",
        "分析": "analysis",
        "理论": "analysis",
    }
    return aliases.get(text, "unknown")  # type: ignore[return-value]


def validate_report(report: PaperReport) -> List[str]:
    errors: List[str] = []
    if not report.title or report.title == "未命名论文":
        errors.append("title is required")
    if not report.authors or report.authors == ["未提及"]:
        errors.append("authors are required")
    if len(report.core_innovations) < 1:
        errors.append("at least one core innovation is required")
    if report.paper_type == "dataset" and report.dataset_info is None:
        errors.append("dataset paper requires dataset_info")
    if report.paper_type == "model" and report.figure is None:
        errors.append("model paper requires figure")
    if report.paper_type in {"industrial", "analysis"} and report.flowchart is None:
        errors.append(f"{report.paper_type} paper requires flowchart")
    if report.paper_type == "model" and len(report.core_formulas) < 1:
        errors.append("model paper should have at least one core formula")
    return errors

