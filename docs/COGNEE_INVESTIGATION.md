# Cognee 功能调查报告

> 2026-04-29 | 全面调查 Cognee 每个功能模块，确认系统完善性

---

## 执行摘要

| 项目 | 结果 |
|------|------|
| **调查范围** | Cognee v1.0.3 全部核心功能：配置、嵌入、向量存储、图存储、搜索 |
| **发现问题** | 2 个关键问题（已修复） |
| **修复后测试结果** | 12/12 通过 |
| **系统状态** | 图谱建立 + 多方式查询 全部正常工作 |

---

## 1. 发现的问题

### 问题 1：所有搜索类型失败（CRITICAL）

**现象**：所有 10 种 `cognee.search()` 报 `SearchPreconditionError: no database/default user found`

**根因**：我们的代码从未调用 `cognee.setup()`，导致：
- 关系型数据库 (SQLite) 未创建
- `default_user` 表不存在
- 搜索函数需要 `get_default_user()`，抛出 `DatabaseNotCreatedError`

**修复**：
- 新建 `src/config/cognee_init.py` 集中初始化模块
- 在 `add_data_points` 前自动调用 `await cognee_setup()`
- 已更新：`extraction/pipeline.py`、`taxonomy/builder.py`、`pipeline/citations.py`

### 问题 2：Kuzu 图数据库损坏

**现象**：`std::bad_alloc` 内存错误

**根因**：Kuzu DB 文件 (`cognee_graph_kuzu`) 损坏

**修复**：删除损坏文件，系统自动重建

---

## 2. 验证结果详情

### 2.1 配置层

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 向量数据库配置 | 通过 | LanceDB, 路径自动解析 |
| 嵌入配置 | 通过 | fastembed, jina-v3, 1024d |
| 图数据库配置 | 通过 | Kuzu, 自动创建 |

### 2.2 引擎层

| 检查项 | 状态 | 详情 |
|--------|------|------|
| Embedding Engine | 通过 | `FastembedEmbeddingEngine`，本地嵌入 |
| Vector Engine | 通过 | `LanceDBAdapter`，自动连接 |
| Graph Engine | 通过 | `KuzuAdapter`，正常读写 |
| Unified Engine | 通过 | 图+向量协调工作 |

### 2.3 存储层

| 检查项 | 状态 | 验证方式 |
|--------|------|----------|
| add_data_points | 通过 | 6 个 DataPoint 同时写入 |
| 图节点存储 | 通过 | `has_node()` 确认存在 |
| 向量集合创建 | 通过 | LanceDB 自动创建 `{Type}_{field}` 表 |
| 向量数据写入 | 通过 | 查询确认 2+ 行/表 |
| 向量搜索 | 通过 | cosine 相似度搜索返回结果 |

### 2.4 搜索层（全部 10 种）

| 搜索类型 | 状态 | 说明 |
|----------|------|------|
| `GRAPH_COMPLETION` | 通过 | 图遍历搜索 |
| `RAG_COMPLETION` | 通过 | RAG 向量+文本搜索 |
| `TRIPLET_COMPLETION` | 通过 | 三元组搜索 |
| `SUMMARIES` | 通过 | 摘要搜索 |
| `CHUNKS` | 通过 | 语义块搜索 |
| `CHUNKS_LEXICAL` | 通过 | 词法块搜索 |
| `GRAPH_COMPLETION_DECOMPOSITION` | 通过 | 分解搜索 |
| `GRAPH_SUMMARY_COMPLETION` | 通过 | 图摘要搜索 |
| `CYPHER` | 通过 | Cypher 查询 |
| `NATURAL_LANGUAGE` | 通过 | 自然语言查询 |

---

## 3. Cognee 内部机制理解

### 3.1 初始化流程（必须）

```
cognee.setup()
    ├── create_relational_db_and_tables()  → SQLite (metadata + users)
    └── create_pgvector_db_and_tables()    → PGVector (如配置)
```

**为什么必须**：搜索需要 `default_user`，用户存储在 relational DB 中。

### 3.2 数据写入流程

```
add_data_points(data_points)
    ├── get_graph_from_model()      → 提取 nodes + edges
    ├── deduplicate_nodes_and_edges() → 去重
    ├── get_unified_engine()
    │   ├── graph = KuzuAdapter
    │   └── vector = LanceDBAdapter
    ├── graph_engine.add_nodes()    → 写入 Kuzu
    └── index_data_points()         → 写入 LanceDB
        ├── 按 (type, field) 分组
        ├── create_vector_index()   → 创建 collection
        └── embed_text() + create_data_points() → 嵌入+存储
```

### 3.3 向量存储格式

LanceDB 中每个 DataPoint 类型 + index_field 创建一个表：

```
TestNode_name        → {id, vector(1024), payload:{text, belongs_to_set}}
TestNode_description → {id, vector(1024), payload:{text, belongs_to_set}}
Paper_title          → {id, vector(1024), payload:{text, belongs_to_set}}
Method_name          → {id, vector(1024), payload:{text, belongs_to_set}}
```

### 3.4 搜索流程

```
cognee.search(query, query_type)
    ├── get_default_user()          → 从 relational DB
    ├── resolve_authorized_datasets() → 权限检查
    └── 按 query_type 分发:
        ├── GRAPH_COMPLETION → GraphCompletionRetriever
        ├── RAG_COMPLETION   → RAGCompletionRetriever (向量+LLM)
        ├── CHUNKS           → ChunksRetriever (LanceDB 向量搜索)
        └── ...
```

---

## 4. 关键文件变更

| 文件 | 变更 | 原因 |
|------|------|------|
| `src/config/cognee_init.py` | 新建 | 集中 Cognee 初始化 |
| `src/config/__init__.py` | 新建 | Python 包标识 |
| `src/extraction/pipeline.py` | 修改 | 导入并调用初始化 |
| `src/taxonomy/builder.py` | 修改 | 导入并调用初始化 |
| `src/pipeline/citations.py` | 修改 | 导入并调用初始化 |

---

## 5. 结论

**系统现已完善**：

- 图谱建立：通过 `add_data_points` 成功同时写入 Kuzu 图数据库和 LanceDB 向量数据库
- 向量查询：通过 LanceDB cosine 搜索验证
- 图查询：通过 Kuzu `has_node` 验证
- 统一查询：通过全部 10 种 `cognee.search()` 类型验证

**建议**：
1. 始终通过 `src.config.cognee_init` 初始化，不要直接调用 Cognee API
2. 如遇 Kuzu `std::bad_alloc`，删除 `cognee_graph_kuzu*` 文件重建
3. 如需清空数据，使用 `await cognee.prune.prune_data()` 和 `await cognee.prune.prune_system(metadata=True)`
