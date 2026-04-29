# 项目文档索引

> 新开发者入门必读。本文档指引你快速了解项目全貌。

---

## 快速导航

| 文档 | 内容 | 适合谁 |
|------|------|--------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 整体架构、数据流、模块职责、设计决策 | 所有开发者 |
| [DATA_MODEL.md](DATA_MODEL.md) | 所有 DataPoint 子类的字段定义、类型、去重机制 | 后端/模型开发者 |
| [PROMPTS.md](PROMPTS.md) | Stage 1a/1b/2 的完整 Prompt 文本和设计 rationale | 算法/Prompt 工程师 |
| [VALIDATION.md](VALIDATION.md) | 测试结果、有效/无效设计、性能数据 | 质量/测试工程师 |
| [KNOWN_ISSUES.md](KNOWN_ISSUES.md) | 所有已知限制、未来优化方向、优先级 | 产品经理/规划者 |

---

## 5 分钟快速入门

### 1. 项目是什么？

把学术论文变成结构化知识图谱：
- 提取方法层级（DIFFCOT → Step-level Forward Noising → Reward-ranked Candidates）
- 提取问题层级（Chain-of-Thought → Error Accumulation → Exposure Bias）
- 提取实验洞察（带证据引用和实体关联）

### 2. 核心技术栈

- **Cognee** (v1.0.3) — 图数据库 (Kuzu) + 向量数据库 (LanceDB)
- **GROBID** — PDF 解析
- **LLM** — Kimi Code / OpenAI / Anthropic
- **Embedding** — fastembed (jinaai/jina-embeddings-v3)

### 3. 核心文件

```
src/extraction/prompts.py    ← LLM Prompt 定义（Stage 1a/1b/2）
src/extraction/pipeline.py   ← 提取管道主逻辑
src/models/academic_nodes.py ← 数据模型定义
src/resolution/resolver.py   ← 实体去重/归一化
src/taxonomy/builder.py      ← 递归分类树
```

### 4. 运行测试

```bash
# 启动 GROBID
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0

# 运行测试
python tests/comprehensive_pipeline_test.py
```

### 5. 关键设计决策（必读）

1. **三阶段分离** — 不混合提取目标，降低 LLM 认知负荷
2. **元数据注入** — 每个 Prompt 强制注入论文标题，消除 "this_paper"
3. **DataPoint 关系容器** — Cognee 不支持复杂关系类型，用显式节点存储
4. **不修改 Cognee 库** — 在之上构建，但分发时打包完整修改版

---

## 已验证有效的设计 ✅

- 三阶段提取（比单阶段多 400% 方法）
- ACRONYM RULE（消除全名/缩写重复）
- Related Work 隔离（无 baseline 污染）
- 预训练模型 = Method（避免 Resource 膨胀）
- EntityResolver 批次内去重（6→5 干净方法）
- 递归 Taxonomy Builder（生成合理根节点）

## 已淘汰的设计 ❌

- Paper Type 检测（类型偏见）
- 单阶段全量提取（质量差）
- 数量限制（遗漏子方法）
- Problem.parent 字段（不创建图边）

---

## 推荐阅读顺序

1. **先看** [VALIDATION.md](VALIDATION.md) — 了解系统能做什么、不能做什么
2. **再看** [ARCHITECTURE.md](ARCHITECTURE.md) — 理解整体架构
3. **深入** [DATA_MODEL.md](DATA_MODEL.md) — 理解数据结构
4. **细节** [PROMPTS.md](PROMPTS.md) — 理解 LLM 交互
5. **规划** [KNOWN_ISSUES.md](KNOWN_ISSUES.md) — 了解下一步方向
