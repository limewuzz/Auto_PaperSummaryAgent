# Paper Report Agent

An automated system that converts academic papers into structured, demo-style reading reports with low hallucination and high consistency.

## Overview

This agent extracts structured information from PDF papers and renders them into standardized Markdown reports. Unlike single-shot summarizers, it uses a modular pipeline to ensure reliable extraction and conservative output.

### Key Features

- **Structured Extraction**: Extracts title, authors, core innovations, formulas, method summaries, and type-specific facts
- **Figure Handling**: Verifies and selects core figures, or generates Mermaid flowcharts when images are unavailable
- **Conservative Output**: Uses `not_reported` for missing fields to avoid hallucination
- **Multi-modal Support**: Works with PDF text and extracted images
- **Modular Design**: Separates parsing, extraction, verification, and rendering for better control

## Installation

```bash
pip install -r requirements.txt
```

For development from the original project root:

```bash
pip install -e .
```

## Quick Start

### Using a JSON spec

```bash
PYTHONPATH=src python -m paper_report_agent --spec samples/report_spec.json --output reports/sample_report.md
```

### Using a PDF with MiniMax API

```bash
MIMO_API_KEY="YOUR_API_KEY" \
MIMO_BASE_URL="https://api.minimaxi.com/v1" \
MIMO_MODEL="MiniMax-M3" \
MIMO_VISION_MODEL="MiniMax-M3" \
PYTHONPATH=src python -m paper_report_agent --pdf benchmark/paper_pdf/01_DeepSeek-R1.pdf --output reports/01_DeepSeek-R1.md
```

## Benchmark & Evaluation

The system is evaluated on 48 academic papers with human-annotated reference reports.

### Metrics

```text
score = 0.40*root_cause_accuracy
      + 0.20*evidence_hit_rate
      + 0.15*action_precision
      + 0.10*need_admin_accuracy
      + 0.10*low_unsafe_action_rate
      + 0.05*latency_or_cost
```

### Results

| Metric | Agent | Baseline |
|---|---:|---:|
| Average score | 0.6474 | 0.6389 |
| root_cause_accuracy | 0.5664 | 0.5611 |
| evidence_hit_rate | 1.0000 | 1.0000 |
| action_precision | 0.9214 | 0.9312 |
| need_admin_accuracy | 0.2941 | 0.2941 |
| low_unsafe_action_rate | 0.2082 | 0.1341 |

### Quality Diagnostics

| Diagnostic | Agent | Baseline |
|---|---:|---:|
| Avg figure count | 0.84 | 2.82 |
| Avg char count | 1234.22 | 2530.65 |
| Avg suspicious numbers | 6.59 | 18.31 |

The agent produces more concise outputs with fewer unsupported numeric claims compared to the direct baseline.

## Running Evaluation

```bash
python benchmark/run_benchmark.py \
  --pred-path benchmark/results.jsonl \
  --ref-path benchmark/ground_truth.jsonl \
  --output-prefix eval_submission
```

This outputs:
- `eval_submission_alignment.json` - Alignment between predictions and references
- `eval_submission_results.jsonl` - Per-paper metric scores
- `eval_submission_summary.md` - Markdown summary
- `eval_submission_summary.json` - Standard JSON format for scoring

## Quality Diagnostics

Run quality diagnostics to detect over-generation and hallucination risks:

```bash
python benchmark/diagnose_report_quality.py \
  --pred-path benchmark/results.jsonl \
  --output-prefix agent
```

## Project Structure

```
submission/
  src/paper_report_agent/    # Agent source code
  benchmark/
    cases.jsonl              # Test cases
    ground_truth.jsonl       # Reference answers
    results.jsonl            # Agent outputs
    run_benchmark.py         # Evaluation script
    diagnose_report_quality.py  # Quality diagnostics
  logs/                      # Output logs
  docs/                      # Documentation
```

## System Design

The agent pipeline consists of:

1. **PDF Parser**: Extracts text and candidate images from PDFs
2. **Module 1**: Structured extraction (paper type, innovations, method summary)
3. **Module 2**: Formula and figure explanation extraction
4. **Figure Verifier**: Decides whether to use extracted figures or generate flowcharts
5. **Renderer**: Produces Markdown reports with fixed sections

This modular approach reduces uncertainty compared to single-shot LLM calls and enables better control over output quality.

## Known Issues

- `benchmark/paper_pdf/46_RedPajama.pdf` contains a different paper (controlled diffusions) than expected
- Type classification accuracy (`need_admin_accuracy`) has room for improvement
- Latency/cost metrics are not available in offline evaluation

## Future Work

- Real-time latency and cost tracking
- Enhanced paper type classification
- Stronger visual models for figure understanding
- Incremental updates for paper revisions
- Human-in-the-loop feedback for continuous improvement

## License

See project license file for details.
