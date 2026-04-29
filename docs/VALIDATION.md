# 验证结果文档 (Validation Results)

> 本文档记录所有测试验证结果，标明哪些设计有效、哪些无效、哪些待验证。

---

## 1. 测试论文

| 属性 | 值 |
|------|-----|
| 标题 | DIFFCOT: Diffusion-styled Chain-of-Thought Reasoning in LLMs |
| 类型 | 方法论文 (Method Paper) |
| 领域 | NLP / LLM 推理 |
| 章节数 | 15 |
| 总字符数 | 31,375 |

---

## 2. 提取精度验证

### 2.1 Stage 1a: 顶层实体

| 实体类型 | 预期 | 实际 | 状态 |
|----------|------|------|------|
| Top-level Methods | 1 | 1 (DIFFCOT) | ✅ 正确 |
| Problems | 3 | 3 | ✅ 正确 |
| Resources | 2 (datasets) | 2 (MATH-1, SVAMP) | ✅ 正确 |

**质量检查**:
- ❌ 无 "this_paper" 悬空关系 — ✅ 通过
- ❌ 无 Related Work 污染 — ✅ 通过
- ❌ 无模型混入 Resource — ✅ 通过

### 2.2 Stage 1b: 子方法

| 指标 | 预期 | 实际 | 状态 |
|------|------|------|------|
| Sub-methods | 4 | 4 | ✅ 正确 |
| Contains 关系 | 4 | 4 | ✅ 正确 |

**层级结构验证**:
```
DIFFCOT contains Step-level Forward Noising — ✅
DIFFCOT contains Diffusion Sliding-Window Mechanism — ✅
DIFFCOT contains Causal Diffusion Noise — ✅
Step-level Forward Noising contains Reward-ranked Candidate Collection — ✅
```

### 2.3 Stage 2: Insight

| 指标 | 预期 | 实际 | 状态 |
|------|------|------|------|
| Insights | 1-3 | 3 | ✅ 正确 |
| 有证据引用 | 3/3 | 3/3 | ✅ 正确 |
| 精确关联实体 | 3/3 | 3/3 | ✅ 正确 |

### 2.4 数据库质量

| 检查项 | 结果 | 状态 |
|--------|------|------|
| 空节点名称 | 0 | ✅ |
| 重复节点 | 0 | ✅ |
| 总节点数 | 17 | — |
| 总边数 | 21 | — |

---

## 3. 设计决策验证

### 3.1 已验证有效 ✅

| 决策 | 验证方式 | 结果 |
|------|----------|------|
| **三阶段分离** | 对比单阶段 vs 三阶段 | 三阶段提取多 400% 方法，无关联错误 |
| **元数据注入** | 检查 relation subject_name | 全部使用真实论文标题，无 "this_paper" |
| **ACRONYM RULE** | 检查方法名重复 | 消除 "DIFFCOT" + "Diffusion-styled Chain of Thought" 重复 |
| **Related Work 隔离** | 检查提取的方法列表 | 无 baseline 方法（CPO, ToT）被误提取 |
| **预训练模型 = Method** | 检查 Resource 列表 | Qwen3-8B, LLaMA 未出现在 Resource 中 |
| **DataPoint 关系容器** | 检查 DB 边 | PaperRelations/MethodRelations/ProblemRelations 正确创建边 |
| **EntityResolver 批次内去重** | 对比输入输出 | 6 个原始方法 → 5 个干净方法 |
| **递归 Taxonomy Builder** | 检查输出树 | 生成合理的根节点（"Diffusion-based Chain-of-Thought Reasoning"） |
| **fastembed 本地嵌入** | 检查 embedding 生成 | 成功生成，无外部 API 依赖 |

### 3.2 已验证无效 / 已淘汰 ❌

| 决策 | 问题 | 淘汰版本 |
|------|------|----------|
| **Paper Type 检测** | 类型偏见导致提取策略偏差 | v4 (2026-04-29) |
| **单阶段全量提取** | 输出质量差、实体关联错误 | v4 (2026-04-29) |
| **数量限制（"提取3-5个"）** | 遗漏子方法和组件 | v4 (2026-04-29) |
| **dummy_embed 全零向量** | sklearn cosine 聚类崩溃 | v3 (替换为 hash-based 伪随机嵌入) |
| **Problem.parent 字段** | Cognee 不自动创建图边 | v2 (替换为 ProblemRelations 显式容器) |

### 3.3 待验证 ⏳

| 决策 | 需要验证的条件 | 当前状态 |
|------|---------------|----------|
| **多论文 Taxonomy 中间层** | 10+ 方法时的递归分组 | 仅测试 5 个方法，LLM 直接汇总为单根 |
| **训练方法提取** | Method 部分输入扩展到 12000+ 字符 | 当前截断在 8000，DPO Loss 等未提取 |
| **Survey 论文支持** | Survey 类型的 Prompt 适配 | 未测试 |
| **多 LLM Provider** | Anthropic, OpenAI, Moonshot 的一致性 | 仅测试 Anthropic (Kimi Code) |
| **大规模 Corpus** | 100+ 论文的实体解析和 Taxonomy | 未测试 |

---

## 4. 性能数据

### 4.1 LLM Token 消耗

| 阶段 | 输入长度 | 输出长度 | 预估 Token |
|------|----------|----------|------------|
| Stage 1a | ~9500 字符 | ~1500 字符 | ~3500 |
| Stage 1b | ~8000 字符 | ~800 字符 | ~2800 |
| Stage 2 | ~6000 字符 | ~1200 字符 | ~2300 |
| **总计** | — | — | **~8600 / 论文** |

### 4.2 运行时间（单论文）

| 步骤 | 耗时 |
|------|------|
| GROBID PDF 解析 | ~5-10s |
| Stage 1a LLM 调用 | ~15-30s |
| Stage 1b LLM 调用 | ~10-20s |
| Stage 2 LLM 调用 | ~10-20s |
| Entity Resolution | ~2-5s |
| DB 写入 | ~3-5s |
| Taxonomy Builder | ~10-20s |
| **总计** | **~55-110s** |

---

## 5. 错误记录

### 5.1 已修复

| 错误 | 原因 | 修复 |
|------|------|------|
| Taxonomy Builder 崩溃 | dummy_embed 返回全零向量 | 替换为 hash-based 伪随机嵌入 |
| 方法名重复 | LLM 同时提取全名和缩写 | ACRONYM RULE + _dedup_batch |
| is_subtask_of 边缺失 | Problem.parent 不创建图边 | 新增 ProblemRelations 容器 |
| 关系名称不匹配 | Resolver 规范化后 relation 未更新 | 关系名称也经过 resolver |
| Resource 为空 | 数据集仅在 Experiments 提及 | Stage 1a 输入加入 Experiments 前 2000 字符 |
| 所有 search 失败 | 未调用 `cognee.setup()`，无 default user | 新增 `src/config/cognee_init.py` 自动初始化 |
| Kuzu `std::bad_alloc` | Kuzu DB 文件损坏 | 删除损坏文件，系统自动重建 |

### 5.2 已知未修复

见 [KNOWN_ISSUES.md](KNOWN_ISSUES.md)
