# Report Quality Diagnostics

## Summary

- **Items**: 49
- **Average diagnostic score**: 52.00
- **Average figure count**: 2.82
- **Average char count**: 2530.65
- **Average unsafe action rate**: 0.9098
- **Average suspicious number count**: 18.31

## Flag Counts

| Flag | Count |
|---|---:|
| many_unverified_numbers | 47 |
| low_reference_title_similarity | 40 |
| number_heavy | 23 |
| too_many_figures | 15 |
| pdf_filename_title_mismatch | 9 |
| too_many_supplements | 6 |
| pdf_filename_title_mismatch_redpajama | 1 |

## Worst Diagnostic Items

| Score | ID | Figures | Unsafe Rate | Flags | Title | Suspicious Numbers |
|---:|---:|---:|---:|---|---|---|
| 35 | 17 | 4 | 1.0000 | too_many_figures, many_unverified_numbers, pdf_filename_title_mismatch, low_reference_title_similarity | Training language models to follow instructions with human feedback | 1.3b, 100倍, 175b, 17t, 2015, 21%, 3%, 4% |
| 35 | 38 | 4 | 1.0000 | too_many_figures, many_unverified_numbers, pdf_filename_title_mismatch, low_reference_title_similarity | Measuring Massive Multitask Language Understanding | 100, 130亿, 14079, 1540, 15908, 1750亿, 175b, 24% |
| 37 | 35 | 4 | 0.9500 | too_many_figures, many_unverified_numbers, number_heavy, pdf_filename_title_mismatch, low_reference_title_similarity | Evaluating Large Language Models Trained on Code | 0.005, 0.17, 0.8, 0.9, 1.0, 100, 12b, 159gb |
| 39 | 30 | 2 | 0.8889 | too_many_supplements, many_unverified_numbers, pdf_filename_title_mismatch, low_reference_title_similarity | ROFORMER: ENHANCED TRANSFORMER WITH ROTARY POSITION EMBEDDING | 10000, 11, 15, 2023, 2104.09864, 3.2, 30, 9 |
| 39 | 44 | 4 | 0.8889 | too_many_figures, many_unverified_numbers, pdf_filename_title_mismatch, low_reference_title_similarity | Dynamic Parallel Tree Search for Efficient LLM Reasoning | 1.5b, 35, 3b, 4×, 6.2%, 7b, 8b, 91.3% |
| 39 | 47 | 4 | 0.8750 | too_many_figures, many_unverified_numbers, pdf_filename_title_mismatch, low_reference_title_similarity | Finetuned Language Models Are Zero-Shot Learners | 10, 11, 12, 128, 137b, 175b, 20, 30k |
| 40 | 43 | 5 | 1.0000 | too_many_figures, too_many_supplements, many_unverified_numbers, number_heavy, low_reference_title_similarity | Artificial Hivemind: The Open-Ended Homogeneity of Language Models (and Beyond) | 0.1, 0.2, 0.8, 0.9, 070, 1.0, 1.5, 10.0% |
| 40 | 46 | 1 | 1.0000 | many_unverified_numbers, pdf_filename_title_mismatch_redpajama, low_reference_title_similarity | CONTROLLED DIFFUSIONS UNDER FULL, PARTIAL AND DECENTRALIZED INFORMATION: EXISTENCE OF OPTIMAL POLICIES AND DISCRETE-TIME APPROXIMATIONS | 03254, 46, 60, 91, 93 |
| 42 | 22 | 2 | 0.9412 | many_unverified_numbers, number_heavy, pdf_filename_title_mismatch, low_reference_title_similarity | DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models | 10.6%, 120b, 14b, 1t, 2021, 22%, 25%, 28% |
| 45 | 23 | 4 | 1.0000 | too_many_figures, many_unverified_numbers, number_heavy, low_reference_title_similarity | Mixtral of Experts | 0, 1.95, 100%, 13b, 14336, 1m, 2.0, 2.1 |
| 46 | 45 | 4 | 0.9744 | too_many_figures, many_unverified_numbers, number_heavy, low_reference_title_similarity | The Pile: An 800GB Dataset of Diverse Text for Language Modeling | 0.02, 0.05, 0.10, 0.28, 0.34, 0.37, 0.4, 0.55 |
| 47 | 12 | 4 | 0.9500 | too_many_figures, many_unverified_numbers, number_heavy, low_reference_title_similarity | GPT-4 Technical Report | 000, 10, 10%, 1000, 10000, 15, 23, 24 |
