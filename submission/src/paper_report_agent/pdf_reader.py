"""PDF 解析模块（基于 PyMuPDF/fitz）。

职责：
- extract_text: 提取 PDF 全文文本（按页拼接），自动清理双栏排版产生的列间空白
- extract_figures: 提取嵌入图片，按面积排序，取最大N张，并记录所在页面文字上下文
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

import fitz  # PyMuPDF


@dataclass
class FigureFile:
    """Metadata for an extracted figure."""

    path: str
    page: int
    width: int
    height: int
    area: int
    context: str = ""  # Surrounding text from the page where the figure appears

    @property
    def label(self) -> str:
        return Path(self.path).stem


def _clean_page_text(raw: str) -> str:
    """清理 PDF 页面的原始文本：合并双栏断行、去连字符、压缩空白。

    双栏 PDF 通过 PyMuPDF 提取后，列间会残留大量空白字符，
    导致单词被切断（如 "goal\n   for"）。此函数将其修复为连续文本。
    """
    # 1. 去掉行尾连字符断词: "goal-\nfor" → "goalfor"
    text = re.sub(r"-\n", "", raw)
    # 2. 把所有空白字符（空格、制表符、换行、列间空白）压缩为单个空格
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text(pdf_path: str) -> str:
    """提取 PDF 全文文本，自动清理双栏排版产生的列间空白。

    每页文本先经过 _clean_page_text 处理（合并断行、去连字符、压缩空白），
    再按空行拼接，保证输出适合 LLM 阅读的连续文本。
    """
    doc = fitz.open(pdf_path)
    pages: List[str] = []
    for page in doc:
        raw = page.get_text("text")
        cleaned = _clean_page_text(raw)
        if cleaned:
            pages.append(cleaned)
    doc.close()
    return "\n\n".join(pages)


def extract_figures(
    pdf_path: str,
    output_dir: str,
    max_figures: int = 3,
    min_area: int = 10000,
) -> List[FigureFile]:
    """提取 PDF 中的嵌入图片，按面积从大到小排序。

    Args:
        pdf_path: PDF 文件路径
        output_dir: 图片保存目录
        max_figures: 最多提取图片数（默认3）
        min_area: 最小像素面积阈值，过滤 icon/logo（默认10000）

    Returns:
        FigureFile 列表，包含图片路径、尺寸、页面文字上下文
    """
    doc = fitz.open(pdf_path)
    os.makedirs(output_dir, exist_ok=True)

    candidates: List[dict] = []

    for page_num, page in enumerate(doc):
        page_text = page.get_text("text").strip()
        image_list = page.get_images(full=True)
        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
            except Exception:
                continue

            if not base_image:
                continue

            width = base_image["width"]
            height = base_image["height"]
            area = width * height

            if area < min_area:
                continue

            candidates.append({
                "xref": xref,
                "page": page_num,
                "width": width,
                "height": height,
                "area": area,
                "ext": base_image["ext"],
                "image": base_image["image"],
                "context": page_text[:1000],  # First 1000 chars of page text
            })

    doc.close()

    # Sort by area descending, take top N
    candidates.sort(key=lambda x: x["area"], reverse=True)
    selected = candidates[:max_figures]

    figures: List[FigureFile] = []
    pdf_stem = Path(pdf_path).stem

    for idx, cand in enumerate(selected, start=1):
        filename = f"{pdf_stem}_fig{idx}.{cand['ext']}"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(cand["image"])
        figures.append(
            FigureFile(
                path=filepath,
                page=cand["page"],
                width=cand["width"],
                height=cand["height"],
                area=cand["area"],
                context=cand.get("context", ""),
            )
        )

    return figures
