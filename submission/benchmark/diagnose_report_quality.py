#!/usr/bin/env python3
"""Diagnostic quality metrics for paper-report JSONL outputs."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

BENCHMARK_DIR = Path(__file__).parent
DEFAULT_REF = BENCHMARK_DIR / "ground_truth.jsonl"
DEFAULT_PDF_DIR = BENCHMARK_DIR / "../benchmark/paper_pdf"

NUMBER_RE = re.compile(r"(?<![\w])\d+(?:\.\d+)?\s*(?:%|k|m|b|t|万|亿|千|百|tokens?|token|billion|million|gb|mb|gpu|hours?|小时|参数|分|倍|×)?", re.I)
NOT_REPORTED = {"", "not_reported", "未提及", "none", "null", "n/a", "na"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose over-generation, mismatch, and hallucination risks.")
    parser.add_argument("--pred-path", required=True)
    parser.add_argument("--ref-path", default=str(DEFAULT_REF))
    parser.add_argument("--pdf-dir", default=str(DEFAULT_PDF_DIR))
    parser.add_argument("--output-prefix", required=True)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def compact(text: Any) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", norm(text))


def tokens(text: Any) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9.+-]*|[\u4e00-\u9fff]", norm(text)))


def jaccard(a: Any, b: Any) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def to_text(value: Any) -> str:
    if isinstance(value, dict):
        return "\n".join(to_text(v) for v in value.values())
    if isinstance(value, list):
        return "\n".join(to_text(v) for v in value)
    return str(value or "")


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, list):
        return len(value) == 0 or all(is_missing(x) for x in value)
    return norm(to_text(value)) in NOT_REPORTED


def extract_numbers(value: Any) -> set[str]:
    found = set()
    for match in NUMBER_RE.finditer(to_text(value)):
        token = re.sub(r"\s+", "", match.group(0).lower())
        if token not in {"1", "2", "3", "4", "5"}:
            found.add(token)
    return found


def split_innovations(text: str) -> list[str]:
    lines = []
    for line in str(text or "").splitlines():
        stripped = re.sub(r"^\s*(?:[-*]\s*)?(?:\d+[.)、]\s*)?", "", line).strip()
        if stripped:
            lines.append(stripped)
    if len(lines) > 1:
        return lines
    return [x.strip() for x in re.split(r"(?<=[。；;])\s*", str(text or "")) if x.strip()]


def expected_title_from_pdf(pdf_dir: Path, paper_id: int) -> str:
    matches = sorted(pdf_dir.glob(f"{paper_id:02d}_*.pdf"))
    if not matches:
        return ""
    stem = matches[0].stem
    return re.sub(r"^\d+_", "", stem).replace("_", " ")


def diagnose_row(row: dict[str, Any], refs_by_id: dict[int, dict[str, Any]], pdf_dir: Path) -> dict[str, Any]:
    paper_id = int(row.get("paper_id") or 0)
    ref = refs_by_id.get(paper_id, {})
    row_text = to_text(row)
    ref_text = to_text(ref)
    pred_nums = extract_numbers(row)
    ref_nums = extract_numbers(ref)
    suspicious_nums = sorted(pred_nums - ref_nums)
    figure_count = len(row.get("figures") or [])
    supplement_count = len(row.get("supplement") or [])
    innovation_count = len(split_innovations(row.get("core_innovation", "")))
    expected_from_pdf = expected_title_from_pdf(pdf_dir, paper_id)
    title = row.get("title", "")
    title_ref_sim = jaccard(title, ref.get("title", "")) if ref else 0.0
    title_pdf_sim = jaccard(title, expected_from_pdf) if expected_from_pdf else 0.0
    redpajama_mismatch = "redpajama" in compact(expected_from_pdf) and "redpajama" not in compact(title)
    duplicateish_id_title_mismatch = bool(expected_from_pdf) and title_pdf_sim < 0.05

    over_generation_flags = []
    if figure_count > 3:
        over_generation_flags.append("too_many_figures")
    if len(row_text) > 9000:
        over_generation_flags.append("row_too_long")
    if len(str(row.get("core_innovation", ""))) > 1200:
        over_generation_flags.append("innovation_too_long")
    if supplement_count > 3:
        over_generation_flags.append("too_many_supplements")

    hallucination_flags = []
    unsafe_rate = len(suspicious_nums) / len(pred_nums) if pred_nums else 0.0
    if unsafe_rate > 0.6 and len(suspicious_nums) >= 3:
        hallucination_flags.append("many_unverified_numbers")
    if len(pred_nums) >= 20:
        hallucination_flags.append("number_heavy")

    mismatch_flags = []
    if redpajama_mismatch:
        mismatch_flags.append("pdf_filename_title_mismatch_redpajama")
    elif duplicateish_id_title_mismatch and title_ref_sim < 0.2:
        mismatch_flags.append("pdf_filename_title_mismatch")
    if ref and title_ref_sim < 0.18:
        mismatch_flags.append("low_reference_title_similarity")

    missing_fields = [k for k in ["title", "authors", "core_innovation", "figures", "supplement"] if is_missing(row.get(k))]
    no_refusal_risk = 0
    for key in ["authors", "core_innovation", "figures", "supplement"]:
        if ref and is_missing(ref.get(key)) and not is_missing(row.get(key)):
            no_refusal_risk += 1

    diagnostic_score = 100
    diagnostic_score -= min(25, 5 * len(over_generation_flags))
    diagnostic_score -= min(35, round(unsafe_rate * 35))
    diagnostic_score -= min(25, 10 * len(mismatch_flags))
    diagnostic_score -= min(15, 5 * len(missing_fields))
    diagnostic_score -= min(15, 5 * no_refusal_risk)
    diagnostic_score = max(0, diagnostic_score)

    return {
        "paper_id": paper_id,
        "title": title,
        "expected_pdf_title_hint": expected_from_pdf,
        "title_ref_similarity": round(title_ref_sim, 4),
        "title_pdf_similarity": round(title_pdf_sim, 4),
        "diagnostic_score": diagnostic_score,
        "figure_count": figure_count,
        "supplement_count": supplement_count,
        "innovation_count": innovation_count,
        "char_count": len(row_text),
        "number_count": len(pred_nums),
        "suspicious_number_count": len(suspicious_nums),
        "unsafe_action_rate": round(unsafe_rate, 4),
        "suspicious_numbers_sample": suspicious_nums[:15],
        "missing_fields": missing_fields,
        "no_refusal_risk_count": no_refusal_risk,
        "flags": over_generation_flags + hallucination_flags + mismatch_flags,
    }


def write_outputs(items: list[dict[str, Any]], prefix: str) -> None:
    out_jsonl = BENCHMARK_DIR / f"{prefix}_quality_diagnostics.jsonl"
    out_md = BENCHMARK_DIR / f"{prefix}_quality_diagnostics.md"
    out_jsonl.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in items) + "\n", encoding="utf-8")

    avg = lambda xs: sum(xs) / len(xs) if xs else 0.0
    flag_counter = Counter(flag for item in items for flag in item["flags"])
    worst = sorted(items, key=lambda x: x["diagnostic_score"])[:12]
    lines = [
        "# Report Quality Diagnostics",
        "",
        "## Summary",
        "",
        f"- **Items**: {len(items)}",
        f"- **Average diagnostic score**: {avg([x['diagnostic_score'] for x in items]):.2f}",
        f"- **Average figure count**: {avg([x['figure_count'] for x in items]):.2f}",
        f"- **Average char count**: {avg([x['char_count'] for x in items]):.2f}",
        f"- **Average unsafe action rate**: {avg([x['unsafe_action_rate'] for x in items]):.4f}",
        f"- **Average suspicious number count**: {avg([x['suspicious_number_count'] for x in items]):.2f}",
        "",
        "## Flag Counts",
        "",
        "| Flag | Count |",
        "|---|---:|",
    ]
    for flag, count in flag_counter.most_common():
        lines.append(f"| {flag} | {count} |")
    lines.extend([
        "",
        "## Worst Diagnostic Items",
        "",
        "| Score | ID | Figures | Unsafe Rate | Flags | Title | Suspicious Numbers |",
        "|---:|---:|---:|---:|---|---|---|",
    ])
    for item in worst:
        flags = ", ".join(item["flags"])
        nums = ", ".join(item["suspicious_numbers_sample"][:8])
        title = str(item["title"]).replace("|", "\\|")
        lines.append(f"| {item['diagnostic_score']} | {item['paper_id']} | {item['figure_count']} | {item['unsafe_action_rate']:.4f} | {flags} | {title} | {nums} |")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Diagnostics: {out_jsonl}")
    print(f"Summary:     {out_md}")


def main() -> int:
    args = parse_args()
    rows = load_jsonl(Path(args.pred_path))
    refs = load_jsonl(Path(args.ref_path))
    refs_by_id = {int(r.get("paper_id") or 0): r for r in refs}
    items = [diagnose_row(row, refs_by_id, Path(args.pdf_dir)) for row in rows]
    write_outputs(items, args.output_prefix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
