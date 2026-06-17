#!/usr/bin/env python3
"""Offline evaluation for generated paper reports against the standard benchmark."""

from __future__ import annotations

import json
import math
import re
import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BENCHMARK_DIR = Path(__file__).parent
PRED_PATH = BENCHMARK_DIR / "results.jsonl"
REF_PATH = BENCHMARK_DIR / "ground_truth.jsonl"
REPORTS_DIR = BENCHMARK_DIR / "../logs"
ALIGNMENT_PATH = BENCHMARK_DIR / "eval_alignment.json"
RESULTS_PATH = BENCHMARK_DIR / "eval_results.jsonl"
SUMMARY_PATH = BENCHMARK_DIR / "eval_summary.md"

WEIGHTS = {
    "root_cause_accuracy": 0.40,
    "evidence_hit_rate": 0.20,
    "action_precision": 0.15,
    "need_admin_accuracy": 0.10,
    "low_unsafe_action_rate": 0.10,
    "latency_or_cost": 0.05,
}

FIELD_NAMES = ["title", "authors", "core_innovation", "figures", "supplement"]
NOT_REPORTED_VALUES = {"", "未提及", "not_reported", "none", "null", "n/a", "na"}
STOPWORDS = {
    "the", "and", "of", "in", "to", "for", "with", "a", "an", "on", "by", "is", "are",
    "论文", "提出", "方法", "模型", "数据", "通过", "实现", "核心", "创新", "系统", "训练",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline evaluation for paper report JSONL outputs.")
    parser.add_argument("--pred-path", default=str(PRED_PATH))
    parser.add_argument("--ref-path", default=str(REF_PATH))
    parser.add_argument("--reports-dir", default=str(REPORTS_DIR))
    parser.add_argument("--output-prefix", default="eval")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    items = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def dump_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_text(text: Any) -> str:
    text = str(text or "").lower()
    text = re.sub(r"[`*_#>|$\\]", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^\w\u4e00-\u9fff.%+-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: Any) -> list[str]:
    norm = normalize_text(text)
    raw = re.findall(r"[a-z0-9][a-z0-9.+-]*|[\u4e00-\u9fff]", norm)
    return [tok for tok in raw if tok not in STOPWORDS and len(tok.strip()) > 0]


def token_f1(a: Any, b: Any) -> float:
    a_tokens = tokenize(a)
    b_tokens = tokenize(b)
    if not a_tokens and not b_tokens:
        return 1.0
    if not a_tokens or not b_tokens:
        return 0.0
    ca = Counter(a_tokens)
    cb = Counter(b_tokens)
    overlap = sum((ca & cb).values())
    if overlap == 0:
        return 0.0
    precision = overlap / sum(ca.values())
    recall = overlap / sum(cb.values())
    return 2 * precision * recall / (precision + recall)


def value_to_text(value: Any) -> str:
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.extend(str(v) for v in item.values() if not isinstance(v, (list, dict)))
                parts.extend(value_to_text(v) for v in item.values() if isinstance(v, (list, dict)))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    if isinstance(value, dict):
        return "\n".join(value_to_text(v) for v in value.values())
    return str(value or "")


def split_innovations(text: str) -> list[str]:
    text = str(text or "").strip()
    if not text:
        return []
    lines = []
    for line in text.splitlines():
        stripped = re.sub(r"^\s*(?:[-*]\s*)?(?:\d+[.)、]\s*)?", "", line).strip()
        if stripped:
            lines.append(stripped)
    if len(lines) > 1:
        return lines
    parts = re.split(r"(?<=[。；;])\s*|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def is_not_reported(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, list):
        return len(value) == 0 or all(is_not_reported(v) for v in value)
    text = normalize_text(value_to_text(value))
    return text in NOT_REPORTED_VALUES


def extract_numbers(text: Any) -> set[str]:
    text = value_to_text(text)
    pattern = r"(?<![\w])\d+(?:\.\d+)?\s*(?:%|k|m|b|t|万|亿|千|百|tokens?|token|billion|million|gb|mb|gpu|hours?|小时|参数|分|倍|×)?"
    nums = set()
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        value = re.sub(r"\s+", "", match.group(0).lower())
        if value and value not in {"1", "2", "3", "4", "5"}:
            nums.add(value)
    return nums


def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", normalize_text(title))


def report_filename_for(pred: dict[str, Any], reports_dir: Path) -> str | None:
    pid = pred.get("paper_id")
    title = title_key(pred.get("title", ""))
    candidates = sorted(reports_dir.glob(f"{int(pid):02d}_*.md")) if isinstance(pid, int) else []
    if len(candidates) == 1:
        return candidates[0].name
    for path in candidates:
        if title and title_key(path.stem).find(title[:12]) >= 0:
            return path.name
    return candidates[0].name if candidates else None


def build_alignment(refs: list[dict[str, Any]], preds: list[dict[str, Any]], reports_dir: Path) -> list[dict[str, Any]]:
    unused_pred_indexes = set(range(len(preds)))
    alignment = []
    for ref in refs:
        scored = []
        for idx in unused_pred_indexes:
            pred = preds[idx]
            title_score = token_f1(pred.get("title", ""), ref.get("title", ""))
            id_bonus = 0.08 if pred.get("paper_id") == ref.get("paper_id") else 0.0
            score = min(1.0, title_score + id_bonus)
            scored.append((score, title_score, idx))
        scored.sort(reverse=True)
        if scored and scored[0][0] >= 0.18:
            score, title_score, pred_idx = scored[0]
            unused_pred_indexes.remove(pred_idx)
            pred = preds[pred_idx]
            status = "matched" if score >= 0.45 else "low_confidence"
            alignment.append({
                "ref_paper_id": ref.get("paper_id"),
                "pred_index": pred_idx,
                "pred_paper_id": pred.get("paper_id"),
                "ref_title": ref.get("title"),
                "pred_title": pred.get("title"),
                "pred_file": report_filename_for(pred, reports_dir),
                "title_similarity": round(title_score, 4),
                "match_score": round(score, 4),
                "status": status,
            })
        else:
            alignment.append({
                "ref_paper_id": ref.get("paper_id"),
                "pred_index": None,
                "pred_paper_id": None,
                "ref_title": ref.get("title"),
                "pred_title": None,
                "pred_file": None,
                "title_similarity": 0.0,
                "match_score": 0.0,
                "status": "unmatched_ref",
            })
    for idx in sorted(unused_pred_indexes):
        pred = preds[idx]
        alignment.append({
            "ref_paper_id": None,
            "pred_index": idx,
            "pred_paper_id": pred.get("paper_id"),
            "ref_title": None,
            "pred_title": pred.get("title"),
            "pred_file": report_filename_for(pred, reports_dir),
            "title_similarity": 0.0,
            "match_score": 0.0,
            "status": "unmatched_pred",
        })
    return alignment


def score_root_cause(pred: dict[str, Any], ref: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    field_scores = {}
    for field in FIELD_NAMES:
        field_scores[field] = token_f1(value_to_text(pred.get(field)), value_to_text(ref.get(field)))
    pred_innov = split_innovations(pred.get("core_innovation", ""))
    ref_innov = split_innovations(ref.get("core_innovation", ""))
    matched = []
    used = set()
    for p in pred_innov:
        best_score = 0.0
        best_idx = None
        for idx, r in enumerate(ref_innov):
            if idx in used:
                continue
            sim = token_f1(p, r)
            if sim > best_score:
                best_score = sim
                best_idx = idx
        if best_idx is not None and best_score >= 0.22:
            used.add(best_idx)
            matched.append({"pred": p, "ref": ref_innov[best_idx], "similarity": round(best_score, 4)})
    field_recall = sum(field_scores.values()) / len(field_scores)
    innovation_recall = min(1.0, len(matched) / max(2, len(ref_innov), 1))
    innovation_two_hit = 1.0 if len(matched) >= 2 else len(matched) / 2
    score = 0.60 * field_recall + 0.25 * innovation_recall + 0.15 * innovation_two_hit
    return clamp(score), {
        "field_scores": {k: round(v, 4) for k, v in field_scores.items()},
        "innovation_match_count": len(matched),
        "pred_innovation_count": len(pred_innov),
        "ref_innovation_count": len(ref_innov),
        "matched_innovations": matched[:5],
    }


def score_evidence(pred: dict[str, Any], ref: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    expected_sections = {
        "authors": "作者",
        "core_innovation": "核心创新点",
        "figures": "核心流程图/流程图",
        "supplement": "补充",
    }
    hits = {}
    for field in expected_sections:
        relevant = token_f1(value_to_text(pred.get(field)), value_to_text(ref.get(field))) >= 0.18
        has_section_value = not is_not_reported(pred.get(field))
        hits[field] = 1.0 if relevant and has_section_value else 0.0 if relevant else None
    scored = [v for v in hits.values() if v is not None]
    score = sum(scored) / len(scored) if scored else 0.0
    return clamp(score), {"proxy": "markdown_section_presence", "field_hits": hits, "expected_sections": expected_sections}


def score_action_precision(pred: dict[str, Any], ref: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    required = {
        "title": not is_not_reported(pred.get("title")),
        "authors": not is_not_reported(pred.get("authors")),
        "core_innovation": len(split_innovations(pred.get("core_innovation", ""))) >= 2,
        "figure_or_flowchart": bool(pred.get("figures")),
        "supplement": bool(pred.get("supplement")),
    }
    format_score = sum(required.values()) / len(required)
    pred_innov = split_innovations(pred.get("core_innovation", ""))
    ref_innov = split_innovations(ref.get("core_innovation", ""))
    precision_hits = 0
    for p in pred_innov:
        if any(token_f1(p, r) >= 0.22 for r in ref_innov):
            precision_hits += 1
    innovation_precision = precision_hits / len(pred_innov) if pred_innov else 0.0
    score = 0.60 * format_score + 0.40 * innovation_precision
    return clamp(score), {"format_blocks": required, "format_score": round(format_score, 4), "innovation_precision": round(innovation_precision, 4)}


def score_need_admin(pred: dict[str, Any], ref: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    checks = {}
    for field in FIELD_NAMES:
        if is_not_reported(ref.get(field)):
            checks[field] = 1.0 if is_not_reported(pred.get(field)) else 0.0
    if not checks:
        return 1.0, {"checked_fields": {}, "note": "no reference not_reported fields"}
    score = sum(checks.values()) / len(checks)
    return clamp(score), {"checked_fields": checks}


def score_low_unsafe(pred: dict[str, Any], ref: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    pred_nums = extract_numbers(pred)
    ref_nums = extract_numbers(ref)
    suspicious = sorted(n for n in pred_nums if n not in ref_nums)
    unsafe_rate = len(suspicious) / len(pred_nums) if pred_nums else 0.0
    score = 1.0 - unsafe_rate
    return clamp(score), {
        "pred_number_count": len(pred_nums),
        "ref_number_count": len(ref_nums),
        "suspicious_numbers": suspicious[:20],
        "unsafe_action_rate": round(unsafe_rate, 4),
    }


def score_latency_or_cost() -> tuple[float | None, dict[str, Any]]:
    return None, {"note": "offline evaluation: latency/cost not available"}


def clamp(value: float) -> float:
    if math.isnan(value):
        return 0.0
    return max(0.0, min(1.0, value))


def weighted_score(metrics: dict[str, float | None]) -> tuple[float, dict[str, float]]:
    used_weight = 0.0
    raw_score = 0.0
    contributions = {}
    for name, weight in WEIGHTS.items():
        value = metrics.get(name)
        if value is None:
            contributions[name] = 0.0
            continue
        raw_score += weight * value
        used_weight += weight
        contributions[name] = round(weight * value, 4)
    normalized = raw_score / used_weight if used_weight else 0.0
    return clamp(normalized), contributions


def evaluate_pair(pred: dict[str, Any], ref: dict[str, Any], alignment_row: dict[str, Any]) -> dict[str, Any]:
    root, root_detail = score_root_cause(pred, ref)
    evidence, evidence_detail = score_evidence(pred, ref)
    precision, precision_detail = score_action_precision(pred, ref)
    need_admin, need_admin_detail = score_need_admin(pred, ref)
    low_unsafe, unsafe_detail = score_low_unsafe(pred, ref)
    latency, latency_detail = score_latency_or_cost()
    metrics = {
        "root_cause_accuracy": root,
        "evidence_hit_rate": evidence,
        "action_precision": precision,
        "need_admin_accuracy": need_admin,
        "low_unsafe_action_rate": low_unsafe,
        "latency_or_cost": latency,
    }
    score, contributions = weighted_score(metrics)
    return {
        "ref_paper_id": alignment_row.get("ref_paper_id"),
        "pred_paper_id": alignment_row.get("pred_paper_id"),
        "pred_file": alignment_row.get("pred_file"),
        "ref_title": ref.get("title"),
        "pred_title": pred.get("title"),
        "alignment_status": alignment_row.get("status"),
        "alignment_score": alignment_row.get("match_score"),
        "score": round(score, 4),
        "metrics": {k: None if v is None else round(v, 4) for k, v in metrics.items()},
        "weighted_contributions": contributions,
        "details": {
            "root_cause_accuracy": root_detail,
            "evidence_hit_rate": evidence_detail,
            "action_precision": precision_detail,
            "need_admin_accuracy": need_admin_detail,
            "low_unsafe_action_rate": unsafe_detail,
            "latency_or_cost": latency_detail,
        },
    }


def write_results(results: list[dict[str, Any]], results_path: Path) -> None:
    with results_path.open("w", encoding="utf-8") as handle:
        for item in results:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def write_summary(results: list[dict[str, Any]], alignment: list[dict[str, Any]], summary_path: Path) -> None:
    matched_results = [r for r in results if r["alignment_status"] == "matched"]
    metric_names = list(WEIGHTS)
    metric_avgs = {}
    for metric in metric_names:
        vals = [r["metrics"][metric] for r in matched_results if r["metrics"][metric] is not None]
        metric_avgs[metric] = average(vals)
    score_avg = average([r["score"] for r in matched_results])
    unsafe_rates = [r["details"]["low_unsafe_action_rate"]["unsafe_action_rate"] for r in matched_results]
    status_counts = Counter(row["status"] for row in alignment)
    low_confidence = [row for row in alignment if row["status"] != "matched"]
    bottom = sorted(matched_results, key=lambda x: x["score"])[:8]
    top = sorted(matched_results, key=lambda x: x["score"], reverse=True)[:5]

    lines = [
        "# Paper Report Offline Evaluation Summary",
        "",
        "## Overall",
        "",
        f"- **Evaluated pairs**: {len(matched_results)}",
        f"- **Average score**: {score_avg:.4f}",
        f"- **Average unsafe action rate**: {average(unsafe_rates):.4f}",
        "- **Latency/cost**: not available in offline mode; scores are normalized over available metrics.",
        "",
        "## Metric Averages",
        "",
        "| Metric | Weight | Average |",
        "|---|---:|---:|",
    ]
    for metric in metric_names:
        value = metric_avgs[metric]
        display = "N/A" if not matched_results or all(r["metrics"][metric] is None for r in matched_results) else f"{value:.4f}"
        lines.append(f"| `{metric}` | {WEIGHTS[metric]:.0%} | {display} |")

    lines.extend([
        "",
        "## Alignment Status",
        "",
        "| Status | Count |",
        "|---|---:|",
    ])
    for status, count in sorted(status_counts.items()):
        lines.append(f"| {status} | {count} |")

    lines.extend([
        "",
        "## Top Scoring Papers",
        "",
        "| Score | Ref ID | Pred ID | Title |",
        "|---:|---:|---:|---|",
    ])
    for item in top:
        lines.append(f"| {item['score']:.4f} | {item['ref_paper_id']} | {item['pred_paper_id']} | {escape_md(item['pred_title'])} |")

    lines.extend([
        "",
        "## Lowest Scoring Papers",
        "",
        "| Score | Ref ID | Pred ID | Title | Main suspicious numbers |",
        "|---:|---:|---:|---|---|",
    ])
    for item in bottom:
        suspicious = ", ".join(item["details"]["low_unsafe_action_rate"].get("suspicious_numbers", [])[:5])
        lines.append(f"| {item['score']:.4f} | {item['ref_paper_id']} | {item['pred_paper_id']} | {escape_md(item['pred_title'])} | {escape_md(suspicious)} |")

    lines.extend([
        "",
        "## Alignment Items Requiring Review",
        "",
        "| Status | Ref ID | Pred ID | Ref Title | Pred Title |",
        "|---|---:|---:|---|---|",
    ])
    for row in low_confidence[:30]:
        lines.append(
            f"| {row['status']} | {row.get('ref_paper_id')} | {row.get('pred_paper_id')} | "
            f"{escape_md(row.get('ref_title'))} | {escape_md(row.get('pred_title'))} |"
        )

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def escape_md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", "<br>")


def main() -> int:
    args = parse_args()
    pred_path = Path(args.pred_path)
    ref_path = Path(args.ref_path)
    reports_dir = Path(args.reports_dir)
    alignment_path = BENCHMARK_DIR / f"{args.output_prefix}_alignment.json"
    results_path = BENCHMARK_DIR / f"{args.output_prefix}_results.jsonl"
    summary_path = BENCHMARK_DIR / f"{args.output_prefix}_summary.md"

    refs = load_jsonl(ref_path)
    preds = load_jsonl(pred_path)
    alignment = build_alignment(refs, preds, reports_dir)
    dump_json(alignment_path, alignment)

    results = []
    for row in alignment:
        if row["status"] != "matched":
            continue
        ref = next(item for item in refs if item.get("paper_id") == row["ref_paper_id"])
        pred = preds[row["pred_index"]]
        results.append(evaluate_pair(pred, ref, row))

    write_results(results, results_path)
    write_summary(results, alignment, summary_path)
    print(f"Alignment: {len(alignment)} rows -> {alignment_path}")
    print(f"Results:   {len(results)} pairs -> {results_path}")
    print(f"Summary:   {summary_path}")

    matched_results = [r for r in results if r["alignment_status"] == "matched"]
    avg = lambda key: sum(r["metrics"][key] for r in matched_results if r["metrics"][key] is not None) / len(matched_results) if matched_results else 0.0
    low_unsafe_rates = [r["metrics"]["low_unsafe_action_rate"] for r in matched_results if r["metrics"]["low_unsafe_action_rate"] is not None]
    low_unsafe_action_rate = sum(low_unsafe_rates) / len(low_unsafe_rates) if low_unsafe_rates else 0.0

    json_output = {
        "agent": "paper_report_agent",
        "total_cases": len(refs),
        "root_cause_accuracy": round(avg("root_cause_accuracy"), 4),
        "evidence_hit_rate": round(avg("evidence_hit_rate"), 4),
        "action_precision": round(avg("action_precision"), 4),
        "unsafe_action_rate": round(1.0 - low_unsafe_action_rate, 4),
        "avg_latency": None,
        "avg_tool_calls": None,
    }
    json_path = BENCHMARK_DIR / f"{args.output_prefix}_summary.json"
    dump_json(json_path, json_output)
    print(f"JSON summary: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
