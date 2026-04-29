# 架构文档 (Architecture)

> 本文档记录 Cognee Research Graph 的完整架构设计，供后续开发者快速理解系统。

---

## 1. 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Entry Points                                │
│  main.py  │  tests/comprehensive_pipeline_test.py  │  examples/basic_usage.py │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Pipeline Orchestration                              │
│                    src/extraction/pipeline.py                                  │
│              AcademicExtractor.extract(paper_struct, paper_id)               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Stage 1a      │    │   Stage 1b      │    │   Stage 2       │
│  Top-Level      │───▶│  Sub-Methods    │───▶│   Insights      │
│  Extraction     │    │  Extraction     │    │   Extraction    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Entity Resolution & Normalization                      │
│                    src/resolution/resolver.py                                  │
│              EntityResolver.resolve_batch(entities)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Graph Storage Layer                                │
│                         Cognee (Kuzu + LanceDB)                              │
│              add_data_points(DataPoint列表) → 图数据库                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Taxonomy Builder (Optional)                          │
│                    src/taxonomy/builder.py                                     │
│              RecursiveTaxonomyBuilder.build_method_tree()                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| **PDF Parser** | `src/parsing/grobid_client.py` | GROBID PDF 解析，输出结构化论文 |
| **Extractor** | `src/extraction/pipeline.py` | 三阶段 LLM 提取管道 |
| **Prompts** | `src/extraction/prompts.py` | Stage 1a/1b/2 的 LLM Prompt 模板 |
| **Models** | `src/models/academic_nodes.py` | DataPoint 子类定义（Paper/Method/Problem/Insight/Resource） |
| **Resolver** | `src/resolution/resolver.py` | 实体归一化、去重、别名映射 |
| **Taxonomy** | `src/taxonomy/builder.py` | 递归分类树构建 |
| **Ingest** | `src/pipeline/ingest.py` | PDF → Cognee 标准 cognify 管道 |
| **Citations** | `src/pipeline/citations.py` | 引用关系提取 |

---

## 3. 数据流

### 3.1 输入流

```
PDF File
    │
    ▼
GrobidClient.parse_pdf() ──▶ PaperStruct
    │
    ├── title: str
    ├── authors: List[str]
    ├── abstract: str
    ├── sections: List[{heading, text}]
    └── references: List[{title, authors, year}]
    │
    ▼
AcademicExtractor.extract(paper_struct, paper_id)
```

### 3.2 提取流

```
PaperStruct
    │
    ├──▶ Stage 1a Prompt (Intro + Method + partial Experiments)
    │       └──▶ {methods: [...], problems: [...], resources: [...], relations: [...]}
    │
    ├──▶ Stage 1b Prompt (Method deep-dive, with top_level_method)
    │       └──▶ {sub_methods: [...], relations: [...]}
    │
    └──▶ Stage 2 Prompt (Experiments, with method_names + problem_names)
            └──▶ {insights: [...]}
    │
    ▼
EntityResolver.resolve_batch({methods, problems, resources})
    │
    ▼
add_data_points([Paper, Method, Problem, Insight, Resource, Relations])
    │
    ▼
Kuzu Graph DB + LanceDB Vector Store
```

### 3.3 存储流

```
DataPoint 子类实例
    │
    ├──▶ Cognee add_data_points()
    │       ├──▶ 生成 UUID (identity_fields 或随机)
    │       ├──▶ 提取 metadata.index_fields → 向量嵌入
    │       ├──▶ 提取关系字段 → 图边
    │       └──▶ 写入 Kuzu (图) + LanceDB (向量)
    │
    └──▶ 查询时
            ├──▶ Kuzu Cypher/MATCH 查询图结构
            └──▶ LanceDB 语义搜索向量相似度
```

---

## 4. 与 Cognee 的集成点

### 4.1 我们使用的 Cognee API

| 接口 | 类型 | 用途 | 稳定性 |
|------|------|------|--------|
| `cognee.add(text, dataset_name)` | 公开 API | 添加原始文本到数据集 | ✅ 稳定 |
| `cognee.cognify(datasets)` | 公开 API | 通用知识图谱提取 | ✅ 稳定 |
| `cognee.config.set_*()` | 公开 API | 配置 embedding/LLM | ✅ 稳定 |
| `cognee.tasks.storage.add_data_points` | **内部 API** | 直接写入 DataPoint | ⚠️ 可能变化 |
| `cognee.infrastructure.engine.DataPoint` | **内部 API** | 基类继承 | ⚠️ 可能变化 |
| `cognee.prune.prune_data/prune_system` | 公开 API | 清理数据库 | ✅ 稳定 |

### 4.2 我们对 Cognee 的修改

| 文件 | 修改 | 原因 |
|------|------|------|
| `cognee/__init__.py` L13-18 | 添加代理变量清除 | 避免 SOCKS 代理冲突 |

---

## 5. 关键设计决策

### 5.1 为什么三阶段分离？

**问题**：单次 LLM 调用同时提取所有内容，输出质量差、实体关联错误。

**决策**：
- Stage 1a：先提取顶层框架（降低认知负荷）
- Stage 1b：在已知 top-level method 后，深入提取子方法
- Stage 2：在已知所有实体后，提取洞察并精确关联

**验证**：DIFFCOT 论文测试显示，三阶段比单阶段提取多 400% 方法，且无关联错误。

### 5.2 为什么用 DataPoint 关系容器？

**问题**：Cognee DataPoint 的关系字段不能直接表达复杂关系类型。

**决策**：创建 `PaperRelations`/`MethodRelations`/`ProblemRelations` 容器节点，显式存储关系边。

**验证**：成功创建 `contains`、`solves`、`is_subtask_of` 等 9 条关系边。

### 5.3 为什么删除 Paper Type 检测？

**问题**：原架构根据论文类型（method/benchmark/survey）切换提取策略，引入偏见。

**决策**：所有论文统一使用三阶段提取，不区分类型。

**验证**：消除了类型误判导致的提取缺失。
