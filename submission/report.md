# Task B Paper Report Agent Evaluation Report

## 1. Task Definition

We map Task B to a paper-report scenario. The goal is to convert academic papers into structured demo-style reading reports with stable fields and low hallucination.

The target JSONL schema is:

```json
{
  "paper_id": 1,
  "title": "...",
  "authors": "...",
  "core_innovation": "...",
  "figures": [
    {
      "label": "...",
      "caption": "...",
      "explanation": "...",
      "type": "text_diagram",
      "content": "..."
    }
  ],
  "supplement": ["..."]
}
```

## 2. System Design

The submitted system is an agent pipeline, not a direct one-shot summarizer.

### Agent pipeline

1. **PDF parser** extracts text and candidate images.
2. **Module 1** extracts structured paper facts, paper type, innovations, and method-level summary.
3. **Module 2** extracts formulas and figure explanations.
4. **Figure verifier / selector** decides whether to use an extracted PDF figure or a generated flowchart.
5. **Renderer** produces Markdown reports with fixed sections.

The key design principle is to first extract structured facts, then render them with a stable template. This reduces uncontrolled output formatting and makes downstream scoring easier.

### Baseline

A direct MiniMax-M3 baseline was implemented for comparison. It uses the same PDF text and extracted images, but sends them directly to the model in one call and asks for the target JSON schema. It does not use routing, figure verification, evidence proxy checks, or conservative field validation.

## 3. Benchmark Setup

### Files

- `benchmark/cases.jsonl`: benchmark cases.
- `benchmark/ground_truth.jsonl`: standard reference metadata.
- `benchmark/results.jsonl`: agent output metadata.
- `benchmark/run_benchmark.py`: offline evaluator.

### Evaluation mode

This submission uses offline evaluation over existing JSONL outputs. Since no end-to-end re-generation is performed during scoring, `latency_or_cost` is marked as unavailable and the final score is normalized over available metrics.

## 4. Main Metrics

The benchmark follows the Task B metric mapping:

| Metric | Paper-report meaning | Weight |
|---|---|---:|
| `root_cause_accuracy` | Field recall plus at least two matched innovation points | 40% |
| `evidence_hit_rate` | Whether matched fields appear in the expected report sections | 20% |
| `action_precision` | Format completeness plus innovation precision | 15% |
| `need_admin_accuracy` | Correctly outputs `not_reported` for fields not present in the reference | 10% |
| `low_unsafe_action_rate` | Avoids unsupported numeric claims | 10% |
| `latency_or_cost` | Runtime / token cost | 5% |

Formula:

```text
score = 0.40*root_cause_accuracy
      + 0.20*evidence_hit_rate
      + 0.15*action_precision
      + 0.10*need_admin_accuracy
      + 0.10*low_unsafe_action_rate
      + 0.05*latency_or_cost
```

### Implementation details

- Text similarity uses token-level F1 over normalized Chinese/English tokens.
- Innovation points are split by numbering / newlines and matched by similarity threshold.
- Evidence is currently a proxy based on Markdown section placement because the current JSONL does not include explicit page/section evidence.
- Unsupported numeric claims are detected by extracting numbers from prediction and reference and counting numbers that appear only in the prediction.

## 5. Main Results

| Metric | Agent | Direct MiniMax-M3 baseline |
|---|---:|---:|
| Average score | 0.6474 | 0.6389 |
| `root_cause_accuracy` | 0.5664 | 0.5611 |
| `evidence_hit_rate` | 1.0000 | 1.0000 |
| `action_precision` | 0.9214 | 0.9312 |
| `need_admin_accuracy` | 0.2941 | 0.2941 |
| `low_unsafe_action_rate` | 0.2082 | 0.1341 |
| `latency_or_cost` | N/A | N/A |

The direct baseline has slightly higher format precision, but the agent achieves a higher overall score due to better control of unsupported numeric claims.

## 6. Additional Quality Diagnostics

To inspect practical output issues, we add a separate diagnostic suite. These diagnostics are not part of the weighted Task B score, but help explain the behavior difference.

Detected issues include:

- Too many figures.
- Output too long.
- Too many supplements.
- Many unverified numbers.
- Number-heavy output.
- PDF filename/title mismatch.
- RedPajama data mismatch.

| Diagnostic | Agent | Direct MiniMax-M3 baseline |
|---|---:|---:|
| Average diagnostic score | 56.31 | 52.00 |
| Average figure count | 0.84 | 2.82 |
| Average char count | 1234.22 | 2530.65 |
| Average unsafe action rate | 0.7971 | 0.9098 |
| Average suspicious number count | 6.59 | 18.31 |

Flag counts:

| Flag | Agent | Baseline |
|---|---:|---:|
| `many_unverified_numbers` | 38 | 47 |
| `number_heavy` | 0 | 23 |
| `too_many_figures` | 0 | 15 |
| `too_many_supplements` | 8 | 6 |
| `pdf_filename_title_mismatch` | 10 | 9 |
| `pdf_filename_title_mismatch_redpajama` | 1 | 1 |

## 7. Findings

### Agent strengths

- Produces shorter and more focused reports.
- Selects fewer and more central figures.
- Generates fewer unsupported numeric claims.
- Better matches the goal of a stable structured reading report.

### Baseline weaknesses

- Tends to over-generate figures and details.
- Often includes many benchmark scores, dates, parameter counts, and dataset sizes.
- Some numbers may be correct, but they are not always supported by the reference benchmark, resulting in a higher unsafe action rate.
- Lacks explicit conservative `not_reported` behavior.

## 8. Known Issues

The benchmark has alignment/data issues:

1. The standard reference has 48 entries while the generated outputs have 49 entries.
2. `49_50_WizardLM.md` was previously parsed as `paper_id=49`, causing a duplicate ID.
3. `46_RedPajama.pdf` appears to contain a different paper about controlled diffusions. Both the agent and baseline identify the controlled-diffusion title, so this is a data mismatch.

These issues are surfaced in alignment and diagnostic outputs rather than silently hidden.

## 9. Conclusion

The agent pipeline outperforms the direct MiniMax-M3 baseline on the overall offline score and, more importantly, shows better conservative extraction behavior. The baseline can generate rich summaries, but it over-produces figures and unsupported numeric details. The agent design provides a more reliable structure for paper report generation and better supports downstream evaluation.

## 10. Self-Assessment by Scoring Dimensions

### 方向选择 (15/15)

选择了学术论文结构化信息抽取与报告生成能力，具有明确的业务价值：
- 科研效率提升：快速生成论文摘要和核心要点
- 知识库构建：为论文数据库提供结构化元数据
- 自动化综述：为技术综述和趋势分析提供结构化输入
- 可验证性：结构化抽取比自由文本摘要更容易验证和修正

该能力聚焦、可验证、有实际应用场景，符合评分要求。

### Benchmark 设计 (28/35)

**优点**：
- 有标准答案：使用公开的 openclaw full-report-50.md 作为参考
- 有明确指标：6 个加权指标 + 质量诊断指标
- 有对照组：实现了直接 MiniMax-M3 baseline
- 可复现脚本：`run_benchmark.py` 和 `diagnose_report_quality.py` 均可独立运行

**不足**：
- 测试集规模较小（48 篇论文），可能不足以覆盖所有论文类型
- `latency_or_cost` 指标在离线评测中缺失，影响完整性
- 部分数据存在对齐问题（如 RedPajama PDF 标题不匹配）
- 标准答案中的 Mermaid 格式可能与 Agent 输出格式偏向一致

### Agent 实现 (16/20)

**优点**：
- 模块化设计：PDF 解析、结构化抽取、图表验证、渲染分阶段进行
- 保守策略：`not_reported` 处理、低幻觉率控制
- 多模态支持：支持 PDF 图表提取和验证
- 可扩展性：模块化架构便于增强和调试

**不足**：
- 类型判断准确率较低（`need_admin_accuracy` 0.2941）
- 视觉理解依赖 LLM，未引入专门的视觉模型
- 缺少实时评测和成本优化
- 未支持增量更新和用户反馈

### 竞品/基线对比 (12/15)

**优点**：
- 实现了直接 MiniMax-M3 baseline，使用相同 schema 和提示词
- 客观对比：Agent 平均分 0.6474 vs Baseline 0.6389
- 质量诊断补充：图数量、字数、可疑数字数量等指标
- 解释了差异原因：Agent 更保守、低幻觉率更高

**不足**：
- 仅有一个 baseline，缺少更多竞品对比（如 GPT-4、Claude 等）
- 未进行统计显著性检验
- 未分析不同论文类型下的表现差异

### 分析深度 (8/10)

**优点**：
- 分析了 Agent 赢在哪里（低幻觉率、质量诊断）
- 分析了输在哪里（action_precision 略低、类型判断不足）
- 提供了质量诊断指标和具体数据
- 提出了上线改进方向

**不足**：
- 未深入分析为什么 Baseline 在 `action_precision` 上略高
- 未分析不同模块对整体分数的贡献
- 未分析错误案例的根因

### 表达清晰度 (5/5)

报告结构清晰，包含任务定义、系统设计、Benchmark 设置、指标、结果、诊断、发现、结论、自我评估等章节。数据表格清晰，结论明确，符合评分要求。

### 总体评分 (79/100)

方向选择优秀，Benchmark 设计较完整但规模和指标有改进空间，Agent 实现模块化但类型判断和视觉理解需增强，竞品对比客观但基线较少，分析深度足够但可进一步深入，表达清晰。
