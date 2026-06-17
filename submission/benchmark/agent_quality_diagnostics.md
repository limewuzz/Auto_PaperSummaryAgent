# Report Quality Diagnostics

## Summary

- **Items**: 49
- **Average diagnostic score**: 56.31
- **Average figure count**: 0.84
- **Average char count**: 1234.22
- **Average unsafe action rate**: 0.7971
- **Average suspicious number count**: 6.59

## Flag Counts

| Flag | Count |
|---|---:|
| low_reference_title_similarity | 40 |
| many_unverified_numbers | 38 |
| pdf_filename_title_mismatch | 10 |
| too_many_supplements | 8 |
| pdf_filename_title_mismatch_redpajama | 1 |

## Worst Diagnostic Items

| Score | ID | Figures | Unsafe Rate | Flags | Title | Suspicious Numbers |
|---:|---:|---:|---:|---|---|---|
| 35 | 17 | 0 | 1.0000 | many_unverified_numbers, pdf_filename_title_mismatch, low_reference_title_similarity | Training language models to follow instructions with human feedback | 17t, 3b, 6b, 7分 |
| 35 | 38 | 0 | 1.0000 | many_unverified_numbers, pdf_filename_title_mismatch, low_reference_title_similarity | Measuring Massive Multitask Language Understanding | 34.5%, 38m, 57, 70%, 89.8%, 95百 |
| 40 | 22 | 1 | 0.8462 | too_many_supplements, many_unverified_numbers, pdf_filename_title_mismatch, low_reference_title_similarity | DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models | 10%, 120b, 2%, 46.8%, 51.7%, 540b, 5m, 82.9% |
| 40 | 30 | 1 | 1.0000 | pdf_filename_title_mismatch, low_reference_title_similarity | RoFormer: Enhanced Transformer with Rotary Position Embedding | 30 |
| 40 | 41 | 0 | 1.0000 | too_many_supplements, many_unverified_numbers, low_reference_title_similarity | The PRISM Alignment Dataset: What Participatory, Representative and Individualised Human Feedback Reveals About the Subjective and Multicultural Alignment of Large Language Models | 2023, 26, 38, 41t, 54, 86, 89 |
| 40 | 46 | 1 | 1.0000 | many_unverified_numbers, pdf_filename_title_mismatch_redpajama, low_reference_title_similarity | Controlled Diffusions Under Full, Partial and Decentralized Information: Existence of Optimal Policies and Discrete-Time Approximations | 2.3, 2.7, 3.1, 4.1, 4.2, 46 |
| 43 | 35 | 1 | 0.9000 | many_unverified_numbers, pdf_filename_title_mismatch, low_reference_title_similarity | Evaluating Large Language Models Trained on Code | 0.8, 100, 12b, 164, 28.8%, 37.7%, 44.5%, 5% |
| 45 | 34 | 1 | 1.0000 | too_many_supplements, many_unverified_numbers, low_reference_title_similarity | COLLABLLM: From Passive Responders to Active Collaborators | 2025, 2502.00640, 34 |
| 45 | 42 | 0 | 1.0000 | many_unverified_numbers, low_reference_title_similarity | TruthfulQA: Measuring How Models Mimic Human Falsehoods | 175b, 38, 42%, 42t, 6, 6%, 7%, 817 |
| 45 | 43 | 0 | 1.0000 | many_unverified_numbers, low_reference_title_similarity | Artificial Hivemind: The Open-Ended Homogeneity of Language Models (and Beyond) | 17, 2025, 23.6%, 25, 250, 26k, 31, 314 |
| 45 | 44 | 1 | 0.8571 | many_unverified_numbers, pdf_filename_title_mismatch, low_reference_title_similarity | Dynamic Parallel Tree Search for Efficient LLM Reasoning | 1.5b, 2%, 3b, 7b, 8b, 91.3% |
| 47 | 32 | 1 | 0.8000 | many_unverified_numbers, pdf_filename_title_mismatch, low_reference_title_similarity | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | 100, 12, 2018, 2100万 |
