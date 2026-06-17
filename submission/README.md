# Auto Report Paper Agent Submission

This submission implements **Task B** in a paper-report scenario: given academic papers, the system extracts structured facts and renders demo-style paper reading reports.

## 1. 你选择了哪个单点能力？

选择了 **学术论文结构化信息抽取与报告生成** 能力。具体包括：
- 从 PDF 论文中提取结构化信息（标题、作者、核心创新、公式、方法总结、类型特定事实）
- 识别和验证核心图表，或生成 Mermaid 流程图
- 渲染为标准化的 Markdown 报告格式

## 2. 为什么这个能力有业务价值？

- **科研效率提升**：快速生成论文摘要和核心要点，帮助研究者快速筛选和消化文献
- **知识库构建**：为论文数据库提供结构化元数据，支持检索和推荐
- **自动化综述**：为技术综述和趋势分析提供结构化输入
- **可验证性**：结构化抽取比自由文本摘要更容易验证和修正

## 3. 你的 benchmark 如何测试这个能力？

Benchmark 包含 48 篇真实学术论文的 PDF，对应人工编写的标准报告。评测指标包括：

```text
score = 0.40*root_cause_accuracy
      + 0.20*evidence_hit_rate
      + 0.15*action_precision
      + 0.10*need_admin_accuracy
      + 0.10*low_unsafe_action_rate
      + 0.05*latency_or_cost
```

- `root_cause_accuracy`：核心创新点提取的 token-level F1 相似度
- `evidence_hit_rate`：证据字段是否包含
- `action_precision`：方法/行动描述的 token-level F1
- `need_admin_accuracy`：类型判断准确性
- `low_unsafe_action_rate`：低幻觉率（避免无依据的数字/行动）
- `latency_or_cost`：延迟/成本（离线评测为 null）

此外还提供质量诊断指标（图数量、字数、可疑数字数量）。

## 4. 你的测试集是否可能偏向自己的 Agent？

测试集来源于公开的标准 benchmark（openclaw full-report-50.md），并非针对本 Agent 设计。可能的偏向包括：
- 标准答案中的 Mermaid 流程图格式与 Agent 输出格式一致
- 但 Baseline 也使用相同的 schema 和提示词，因此格式偏向对两者公平
- 评测指标使用 token-level F1，对长度和格式不敏感，减少风格偏向

## 5. 你的 Agent 相比 baseline 赢在哪里？

Agent 平均分 **0.6474** vs Baseline **0.6389**，主要优势：
- **低幻觉率**：`low_unsafe_action_rate` 0.2082 vs 0.1341，Agent 更保守，避免无依据的数字和行动
- **质量诊断**：Agent 平均可疑数字数量 6.59 vs Baseline 18.31，图数量 0.84 vs 2.82，更简洁
- **模块化设计**：通过分阶段抽取、验证、渲染，减少单次 LLM 调用的不确定性

## 6. 它输在哪里？

- `action_precision` 略低（0.9214 vs 0.9312），可能因保守策略导致细节缺失
- `need_admin_accuracy` 相同（0.2941），类型判断仍有提升空间
- Baseline 单次调用可能更擅长捕捉长文本细节，但伴随更多幻觉

## 7. 如果要上线，下一步应该补什么？

- **实时评测**：补充 `latency_or_cost` 指标，优化多模态调用成本
- **类型判断增强**：改进 paper_type 分类准确率
- **视觉理解**：引入更强的视觉模型提升图表理解能力
- **增量更新**：支持论文版本更新时的增量抽取
- **用户反馈**：加入人工审核和反馈循环，持续优化抽取质量

## What is included

```text
submission/
  README.md
  report.md
  requirements.txt
  src/
    paper_report_agent/
  benchmark/
    cases.jsonl
    ground_truth.jsonl
    run_benchmark.py
    results.jsonl
    agent_eval_summary.md
    baseline_eval_summary.md
    agent_quality_diagnostics.md
    baseline_quality_diagnostics.md
  logs/
  docs/
```

## Method

The submitted agent is a structured paper report pipeline rather than a single-shot summarizer.

Main stages:

1. **PDF parsing**: extract paper text and candidate figures.
2. **Structured extraction**: extract title, authors, paper type, innovations, formulas, method summary, and type-specific facts.
3. **Figure handling**: verify and select core figures when available; otherwise generate a text/Mermaid flowchart.
4. **Validation and rendering**: normalize fields, apply conservative `not_reported` behavior, and render Markdown reports.

A direct MiniMax-M3 baseline was also built for comparison. It sends extracted text and images directly to the model and asks it to return the same JSONL schema, without the agent pipeline.

## Installation

```bash
pip install -r requirements.txt
```

For local development from the original project root:

```bash
pip install -e .
```

## Run the agent

Example using an existing JSON spec:

```bash
PYTHONPATH=src python -m paper_report_agent --spec samples/report_spec.json --output reports/sample_report.md
```

Example using a PDF and MiniMax-compatible API:

```bash
MIMO_API_KEY="YOUR_API_KEY" \
MIMO_BASE_URL="https://api.minimaxi.com/v1" \
MIMO_MODEL="MiniMax-M3" \
MIMO_VISION_MODEL="MiniMax-M3" \
PYTHONPATH=src python -m paper_report_agent --pdf benchmark/paper_pdf/01_DeepSeek-R1.pdf --output reports/01_DeepSeek-R1.md
```

## Benchmark files

- `benchmark/cases.jsonl`: paper cases and source PDF paths.
- `benchmark/ground_truth.jsonl`: reference structured reports parsed from the standard benchmark.
- `benchmark/results.jsonl`: agent output structured reports.
- `benchmark/run_benchmark.py`: offline scoring script.

Run evaluation:

```bash
python benchmark/run_benchmark.py \
  --pred-path benchmark/results.jsonl \
  --ref-path benchmark/ground_truth.jsonl \
  --output-prefix eval_submission
```

The benchmark computes six Task-B-style metrics:

```text
score = 0.40*root_cause_accuracy
      + 0.20*evidence_hit_rate
      + 0.15*action_precision
      + 0.10*need_admin_accuracy
      + 0.10*low_unsafe_action_rate
      + 0.05*latency_or_cost
```

In this offline submission, `latency_or_cost` is unavailable and is set to `null`; the final score is normalized over available metrics.

## Results

Agent vs direct MiniMax-M3 baseline:

| Metric | Agent | Direct MiniMax-M3 baseline |
|---|---:|---:|
| Average score | 0.6474 | 0.6389 |
| root_cause_accuracy | 0.5664 | 0.5611 |
| evidence_hit_rate | 1.0000 | 1.0000 |
| action_precision | 0.9214 | 0.9312 |
| need_admin_accuracy | 0.2941 | 0.2941 |
| low_unsafe_action_rate | 0.2082 | 0.1341 |

Additional quality diagnostics show that the agent is more conservative:

| Diagnostic | Agent | Baseline |
|---|---:|---:|
| Average diagnostic score | 56.31 | 52.00 |
| Average figure count | 0.84 | 2.82 |
| Average char count | 1234.22 | 2530.65 |
| Average unsafe action rate | 0.7971 | 0.9098 |
| Average suspicious number count | 6.59 | 18.31 |

The direct baseline has comparable extraction and format scores but introduces more unsupported numeric claims and over-generates figures. This supports the value of the agent pipeline in conservative extraction and hallucination control.

## Known data issue

`benchmark/paper_pdf/46_RedPajama.pdf` appears to contain a different paper: `CONTROLLED DIFFUSIONS UNDER FULL, PARTIAL AND DECENTRALIZED INFORMATION...`. Both the agent and baseline identify this title, so this is treated as a benchmark data mismatch rather than a model-only error.
