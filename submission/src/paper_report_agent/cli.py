"""CLI 命令行入口。

支持三种输入模式（互斥）：
  --spec FILE        从 JSON spec 生成（不调用 LLM）
  --paper-text FILE  从纯文本走 LLM 抽取
  --pdf FILE         从 PDF 抽取文本+图片，走完整 Agent 流程

用法示例：
  python -m paper_report_agent --pdf paper.pdf --output reports/out.md
  python -m paper_report_agent --paper-text paper.txt --output reports/out.md
  python -m paper_report_agent --spec samples/report_spec.json --output reports/out.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import generate_report_from_pdf, generate_report_from_spec, generate_report_from_text


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="Generate a demo-aligned paper report.")

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--spec", help="Path to structured paper report JSON.")
    input_group.add_argument(
        "--paper-text",
        nargs="+",
        metavar="FILE",
        help="Path(s) to plain-text paper file(s) for LLM extraction.",
    )
    input_group.add_argument(
        "--pdf",
        nargs="+",
        metavar="FILE",
        help="Path(s) to PDF paper file(s). Extracts text + figures, then LLM extraction.",
    )

    # Output
    parser.add_argument("--output", help="Optional output Markdown path.")
    parser.add_argument("--title", default="论文拆解报告", help="Report title.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on missing required fields instead of emitting warnings.",
    )

    # LLM config
    parser.add_argument("--api-key", help="LLM API key (or set MIMO_API_KEY env).")
    parser.add_argument("--base-url", help="LLM API base URL (or set MIMO_BASE_URL env).")
    parser.add_argument("--model", help="LLM model name (or set MIMO_MODEL env).")

    return parser


def main(argv: list[str] | None = None) -> int:
    """主入口：解析参数 → 调用对应 pipeline → 输出 Markdown。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.spec:
            markdown, warnings = generate_report_from_spec(args.spec, strict=args.strict)
        elif args.pdf:
            # Determine output directory for extracted assets
            if args.output:
                output_dir = str(Path(args.output).expanduser().parent)
            else:
                output_dir = "."
            markdown, warnings = generate_report_from_pdf(
                args.pdf,
                output_dir=output_dir,
                api_key=args.api_key,
                base_url=args.base_url,
                model=args.model,
                title=args.title,
                strict=args.strict,
            )
        else:
            # Read paper text files
            paper_texts = []
            for fpath in args.paper_text:
                text = Path(fpath).expanduser().read_text(encoding="utf-8")
                paper_texts.append(text)
            markdown, warnings = generate_report_from_text(
                paper_texts,
                api_key=args.api_key,
                base_url=args.base_url,
                model=args.model,
                title=args.title,
                strict=args.strict,
            )
    except Exception as exc:  # noqa: BLE001 - CLI should report all failures cleanly.
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

