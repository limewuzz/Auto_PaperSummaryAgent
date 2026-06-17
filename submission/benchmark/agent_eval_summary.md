# Paper Report Offline Evaluation Summary

## Overall

- **Evaluated pairs**: 34
- **Average score**: 0.6474
- **Average unsafe action rate**: 0.7918
- **Latency/cost**: not available in offline mode; scores are normalized over available metrics.

## Metric Averages

| Metric | Weight | Average |
|---|---:|---:|
| `root_cause_accuracy` | 40% | 0.5664 |
| `evidence_hit_rate` | 20% | 1.0000 |
| `action_precision` | 15% | 0.9214 |
| `need_admin_accuracy` | 10% | 0.2941 |
| `low_unsafe_action_rate` | 10% | 0.2082 |
| `latency_or_cost` | 5% | N/A |

## Alignment Status

| Status | Count |
|---|---:|
| low_confidence | 8 |
| matched | 34 |
| unmatched_pred | 7 |
| unmatched_ref | 6 |

## Top Scoring Papers

| Score | Ref ID | Pred ID | Title |
|---:|---:|---:|---|
| 0.8138 | 7 | 10 | The Llama 3 Herd of Models |
| 0.8079 | 4 | 4 | DeepSeek-VL2: Mixture-of-Experts Vision-Language Models for Advanced Multimodal Understanding |
| 0.7981 | 5 | 5 | Janus-Pro: Unified Multimodal Understanding and Generation with Data and Model Scaling |
| 0.7847 | 6 | 9 | Qwen2.5 Technical Report |
| 0.7752 | 1 | 1 | DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning |

## Lowest Scoring Papers

| Score | Ref ID | Pred ID | Title | Main suspicious numbers |
|---:|---:|---:|---|---|
| 0.4913 | 43 | 39 | Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena | 2023, 39 |
| 0.5037 | 36 | 32 | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | 100, 12, 2018, 2100万, 32 |
| 0.5214 | 35 | 31 | ReAct: Synergizing Reasoning and Acting in Language Models | 31, 540b |
| 0.5279 | 38 | 34 | COLLABLLM: From Passive Responders to Active Collaborators | 2025, 2502.00640, 34 |
| 0.5439 | 14 | 18 | Direct Preference Optimization: Your Language Model is Secretly a Reward Model | 18 |
| 0.5462 | 40 | 36 | From Local to Global: A GraphRAG Approach to Query-Focused Summarization | 36 |
| 0.5800 | 37 | 33 | Toolformer: Language Models Can Teach Themselves to Use Tools | 33t |
| 0.5838 | 41 | 37 | SELF-RAG: LEARNING TO RETRIEVE, GENERATE, AND CRITIQUE THROUGH SELF-REFLECTION | 37 |

## Alignment Items Requiring Review

| Status | Ref ID | Pred ID | Ref Title | Pred Title |
|---|---:|---:|---|---|
| unmatched_ref | 18 | None | GRPO: Group Relative Policy Optimization (DeepSeekMath) |  |
| low_confidence | 19 | 23 | Mixtral 8x7B: A Sparse Mixture of Experts (SMoE) Language Model | Mixtral of Experts |
| low_confidence | 27 | 47 | CLIP: Learning Transferable Visual Models From Natural Language Supervision | Finetuned Language Models Are Zero-Shot Learners |
| low_confidence | 28 | 35 | LLaVA: Large Language and Vision Assistant | Evaluating Large Language Models Trained on Code |
| low_confidence | 29 | 49 | BLIP-2: Bootstrapping Language-Image Pre-training with Frozen Image Encoders and Large Language Models | WizardLM: Empowering Large Pre-trained Language Models to Follow Complex Instructions |
| low_confidence | 30 | 38 | MiniGPT-4: Enhancing Vision-Language Understanding with Advanced Large Language Models | Measuring Massive Multitask Language Understanding |
| unmatched_ref | 31 | None | LLaVA-OneVision: Easy Visual Task Transfer |  |
| unmatched_ref | 32 | None | Qwen2.5-VL: The Latest Flagship Model of Qwen Vision-Language Series |  |
| unmatched_ref | 33 | None | Janus: Decoupling Visual Encoding for Unified Multimodal Understanding and Generation |  |
| unmatched_ref | 34 | None | Kimi K1.5: Scaling Reinforcement Learning with LLMs |  |
| unmatched_ref | 39 | None | Evaluating LLMs Trained on Code (Codex / HumanEval) |  |
| low_confidence | 42 | 7 | MMLU (Massive Multitask Language Understanding) | DeepSeek-VL: Towards Real-World Vision-Language Understanding |
| low_confidence | 45 | 41 | The PRISM Alignment Dataset | The PRISM Alignment Dataset: What Participatory, Representative and Individualised Human Feedback Reveals About the Subjective and Multicultural Alignment of Large Language Models |
| low_confidence | 48 | 49 | Beyond 'Aha!': Toward Systematic Meta-Abilities Alignment in Large Reasoning Models | ShareGPT4V: Improving Large Multi-Modal Models with Better Captions |
| unmatched_pred | None | 6 |  | DeepSeek LLM: 以长期主义视角扩展开源语言模型 |
| unmatched_pred | None | 8 |  | Qwen3 Technical Report |
| unmatched_pred | None | 13 |  | Seed1.5-VL Technical Report |
| unmatched_pred | None | 22 |  | DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models |
| unmatched_pred | None | 44 |  | Dynamic Parallel Tree Search for Efficient LLM Reasoning |
| unmatched_pred | None | 45 |  | The Pile: An 800GB Dataset of Diverse Text for Language Modeling |
| unmatched_pred | None | 46 |  | Controlled Diffusions Under Full, Partial and Decentralized Information: Existence of Optimal Policies and Discrete-Time Approximations |
