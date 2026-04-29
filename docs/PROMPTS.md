# 提示词设计文档 (Prompt Design)

> 本文档记录所有 LLM Prompt 的设计 rationale、完整文本和迭代历史。

---

## 1. 设计原则

### 1.1 核心原则

| 原则 | 说明 |
|------|------|
| **元数据注入** | 每个 Prompt 头部强制注入论文 title/authors/abstract，消除 "this_paper" 悬空引用 |
| **阶段分离** | 单 Prompt 不混合多种提取目标，降低 LLM 认知负荷 |
| **精确关联** | Stage 2 必须接收 Stage 1 的实体列表，强制 exact match |
| **无数量限制** | 不限制提取数量，由 LLM 自行判断 |
| **Related Work 隔离** | 明确指令排除 Related Work 中的方法 |

### 1.2 反模式（已淘汰）

| 反模式 | 问题 | 解决方案 |
|--------|------|----------|
| Paper Type 检测 | 类型偏见导致提取策略偏差 | 删除类型检测，统一 staged extraction |
| 单阶段全量提取 | 输出质量差、实体关联错误 | 三阶段分离 |
| "this_paper" 占位符 | 关系悬空，无法匹配节点 | 强制使用真实论文标题 |
| 数量限制 | 遗漏子方法和组件 | 删除所有数量限制 |

---

## 2. Stage 1a: 顶层实体提取

### 2.1 输入

- Intro (前 2500 字符)
- Method (前 5000 字符)
- Experiments 开头 (前 2000 字符) — 用于提取数据集

### 2.2 Prompt 结构

```
[Paper Metadata Block]
  Title, Authors, Abstract

[Task Description]
  Read INTRODUCTION, METHOD, and EXPERIMENTS sections
  Extract ONLY what THIS paper ORIGINALLY proposes
  Do NOT extract methods merely mentioned as background

[Entity Types]
  1. Method: top-level framework (1 per paper)
  2. Problem: task (broad domain) + challenge (specific difficulty)
  3. Resource: datasets, benchmarks, metrics

[Relation Types]
  Paper→Method: proposes | uses
  Paper→Problem: addresses
  Method→Problem: solves | partially_solves

[Critical Rules]
  - Ignore Related Work mentions
  - proposes ONLY for original contribution
  - Use PAPER TITLE as subject_name
  - Do NOT limit entity counts
  - Pre-trained models are Methods, NOT Resources

[Output Format]
  Strict JSON with entities and relations arrays
```

### 2.3 关键规则

**ACRONYM RULE**: 全名和缩写同时出现时只取缩写
```
"Diffusion-styled Chain of Thought (DIFFCOT)" → 只用 "DIFFCOT"
```

**NORMALIZATION**: 使用论文文本中的最短规范名称

**RESOURCE EXCLUSION**: 预训练模型（Qwen3-8B, LLaMA-3-70B）属于 Method，不属于 Resource

### 2.4 验证结果

| 指标 | DIFFCOT 论文 |
|------|-------------|
| Top-level Methods | 1 (DIFFCOT) |
| Problems | 3 (task + 2 challenges) |
| Resources | 2 (datasets only) |
| Relations | 6 |

**有效** ✅ — 无 Related Work 污染，无模型混入 Resource

---

## 3. Stage 1b: 子方法提取

### 3.1 输入

- Method section (前 8000 字符)
- top_level_method 名称（来自 Stage 1a）

### 3.2 Prompt 结构

```
[Paper Metadata Block]

[Task Description]
  Read METHOD section
  Extract INTERNAL structure of top-level method "{top_level_method}"

[Rules]
  - Extract ONLY novel and central components
  - Use SPECIFIC names from paper text
  - Do NOT extract generic steps (forward pass, gradient descent)
  - ACRONYM RULE: full name + acronym → use acronym only

[Relation Types]
  Method→Method: contains | uses_technique | improves_upon | is_variant_of | combines

[Critical Rules]
  - "{top_level_method}" should be subject of most contains relations
  - contains is the MOST IMPORTANT relation
  - improves_upon ONLY with explicit performance comparison

[Output Format]
  Strict JSON with sub_methods and relations arrays
```

### 3.3 验证结果

| 指标 | DIFFCOT 论文 |
|------|-------------|
| Sub-methods | 4 |
| Contains relations | 4 |

```
DIFFCOT
├── contains → Step-level Forward Noising
│   └── contains → Reward-ranked Candidate Collection
├── contains → Diffusion Sliding-Window Mechanism
└── contains → Causal Diffusion Noise
```

**有效** ✅ — 层级关系完全正确

---

## 4. Stage 2: Insight 提取

### 4.1 输入

- Experiments + Results (前 6000 字符)
- method_names 列表（来自 Stage 1a+1b）
- problem_names 列表（来自 Stage 1a）

### 4.2 Prompt 结构

```
[Paper Metadata Block]

[Task Description]
  Read EXPERIMENTS and RESULTS section
  Extract 1-3 key insights

[Insight Definition]
  What the field LEARNED from this paper, not what the paper DID

[Insight Types]
  - empirical_finding: unexpected experimental result
  - method_innovation: new technique enabling impossible things
  - boundary_condition: when/where a method works or fails
  - negative_result: important disconfirmation
  - theoretical_claim: formal or conceptual reframing

[Rules]
  - Each insight MUST have direct supporting quote
  - Do NOT restate the abstract
  - Confidence: high | medium | low

[Association]
  Available methods: {method_names}
  Available problems: {problem_names}

  related_method_names and related_problem_names MUST use exact names from lists above

[Output Format]
  Strict JSON with insights array
```

### 4.3 验证结果

| # | Type | Confidence | Statement Summary |
|---|------|------------|-------------------|
| 1 | boundary_condition | high | Self-verification methods unstable across models |
| 2 | empirical_finding | high | Local step-wise optimization insufficient |
| 3 | method_innovation | high | Iterative denoising more robust than self-verification |

**有效** ✅ — 全部有证据引用，精确关联实体

---

## 5. Prompt 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0 | 2026-04-28 | 单阶段提取，含 Paper Type 检测 |
| v1 | 2026-04-28 | 细粒度提取，增加 contains/is_subtask_of |
| v2 | 2026-04-28 | 增加批次内去重、ProblemRelations |
| v3 | 2026-04-28 | 递归 Taxonomy Builder |
| **v4** | **2026-04-29** | **三阶段分离、元数据注入、删除 Paper Type、ACRONYM RULE** |

---

## 6. LLM 配置

### 6.1 支持的 Provider

| Provider | API Key Env | Base URL Env | 默认模型 |
|----------|------------|-------------|----------|
| Anthropic (Kimi Code) | `ANTHROPIC_AUTH_TOKEN` | `ANTHROPIC_BASE_URL` | `kimi-for-coding` |
| OpenAI | `OPENAI_API_KEY` | — | `gpt-4` |
| Moonshot | `KIMI_API_KEY` | `LLM_BASE_URL` | `moonshot-v1-8k` |

### 6.2 配置代码

```python
cognee.config.set_embedding_provider("fastembed")
cognee.config.set_embedding_model("jinaai/jina-embeddings-v3")
cognee.config.set_embedding_dimensions(1024)
```
