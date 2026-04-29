# 数据模型规范 (Data Model Specification)

> 本文档定义所有 DataPoint 子类的字段、类型、用途和验证规则。

---

## 1. 核心实体

### 1.1 Paper

```python
class Paper(DataPoint):
    title: str
    authors: List[str]
    abstract: str = ""
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    metadata: dict = {"index_fields": ["title", "abstract"]}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | str | ✅ | 论文标题（去重标识） |
| authors | List[str] | ✅ | 作者列表 |
| abstract | str | | 摘要文本（用于嵌入） |
| year | int | | 发表年份 |
| venue | str | | 会议/期刊 |
| doi | str | | DOI 标识符 |

**identity_fields**: `["title"]` — 相同标题的论文视为同一篇

---

### 1.2 Method

```python
class Method(DataPoint):
    name: str
    description: str = ""
    type: str = "method"  # method | technique | component | baseline
    parent_method: Optional[str] = None  # 仅用于参考，关系通过 MethodRelations 存储
    metadata: dict = {"index_fields": ["name", "description"]}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | ✅ | 方法名称（去重标识） |
| description | str | | 方法描述（用于嵌入） |
| type | str | | 层级类型：method/technique/component/baseline |
| parent_method | str | | 父方法名称（仅参考） |

**type 枚举**:
- `method` — 顶层框架（每篇论文通常 1 个）
- `technique` — 技术/机制（如 Diffusion Sliding-Window）
- `component` — 组件/子模块（如 Reward-ranked Candidate Collection）
- `baseline` — 对比基线方法（如 CPO, ToT）

**identity_fields**: `["name"]`

---

### 1.3 Problem

```python
class Problem(DataPoint):
    name: str
    description: str = ""
    level: str = "task"  # task | challenge | sub_challenge
    parent: Optional[str] = None  # 仅用于参考，关系通过 ProblemRelations 存储
    metadata: dict = {"index_fields": ["name", "description"]}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | ✅ | 问题名称（去重标识） |
| description | str | | 问题描述 |
| level | str | | 层级：task / challenge / sub_challenge |
| parent | str | | 父问题名称（仅参考） |

**level 枚举**:
- `task` — 宽泛任务（如 Chain-of-Thought Reasoning）
- `challenge` — 具体困难（如 Error Accumulation in CoT）
- `sub_challenge` — 细分挑战（如 Local Step-wise Optimization Limitation）

**identity_fields**: `["name"]`

---

### 1.4 Resource

```python
class Resource(DataPoint):
    name: str
    type: str = "dataset"  # dataset | benchmark | metric | tool
    metadata: dict = {"index_fields": ["name"]}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | ✅ | 资源名称 |
| type | str | | 资源类型 |

**type 枚举**:
- `dataset` — 数据集（MATH-1, SVAMP）
- `benchmark` — 基准测试套件
- `metric` — 评估指标（accuracy, BLEU, ROUGE）
- `tool` — 开源工具

**重要规则**: 预训练模型（Qwen3-8B, LLaMA）**不属于 Resource**，属于 Method/baseline。

**identity_fields**: `["name"]`

---

### 1.5 Insight

```python
class Insight(DataPoint):
    statement: str
    type: str = "empirical_finding"  # empirical_finding | method_innovation | boundary_condition | negative_result | theoretical_claim
    confidence: str = "medium"  # high | medium | low
    evidence_quote: str = ""
    from_paper: Optional[Paper] = None
    related_method_names: List[str] = []
    related_problem_names: List[str] = []
    metadata: dict = {"index_fields": ["statement", "evidence_quote"]}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| statement | str | ✅ | 洞察陈述（去重标识） |
| type | str | ✅ | 洞察类型 |
| confidence | str | | 置信度 |
| evidence_quote | str | | 原文引用 |
| from_paper | Paper | | 来源论文 |
| related_method_names | List[str] | | 关联方法名称（必须精确匹配 Method.name） |
| related_problem_names | List[str] | | 关联问题名称（必须精确匹配 Problem.name） |

**type 枚举**:
- `empirical_finding` — 意外实验结果
- `method_innovation` — 新技术突破
- `boundary_condition` — 方法适用边界
- `negative_result` — 重要否定发现
- `theoretical_claim` — 理论/概念重构

**identity_fields**: `["statement"]`

---

## 2. 关系容器

Cognee 的 DataPoint 关系字段无法直接表达复杂关系类型，因此使用**显式关系容器节点**。

### 2.1 PaperRelations

```python
class PaperRelations(DataPoint):
    paper: Paper
    contains_insight: List[Insight] = []
    proposes: List[Method] = []
    addresses: List[Problem] = []
    evaluates_on: List[Resource] = []
```

存储论文的所有 outgoing 关系。

### 2.2 MethodRelations

```python
class MethodRelations(DataPoint):
    method: Method
    contains: List[Method] = []
    uses_technique: List[Method] = []
    solves: List[Problem] = []
    partially_solves: List[Problem] = []
    improves_upon: List[Method] = []
    is_variant_of: List[Method] = []
    combines: List[Method] = []
```

存储方法的所有 outgoing 关系。

### 2.3 ProblemRelations

```python
class ProblemRelations(DataPoint):
    problem: Problem
    is_subtask_of: List[Problem] = []
```

存储问题的层级关系。

---

## 3. 去重机制

### 3.1 Cognee 内置去重

DataPoint 的 `identity_fields` 定义了去重键：
- 相同 `identity_fields` 值的实体 → 同一个图节点
- UUID5 基于 identity_fields 的值生成

### 3.2 批次内去重

`EntityResolver._dedup_batch()` 在写入前进行额外去重：

| 策略 | 触发条件 | 示例 |
|------|----------|------|
| 缩写匹配 | 全名和缩写同时出现 | "DIFFCOT" ← "Diffusion-styled Chain of Thought" |
| Jaccard 相似度 | > 0.8 | "Chain-of-Thought Reasoning" ← "Chain-of-Thought" |
| 子串包含 | 一个是另一个的子串 | "Error Accumulation in CoT" ← "Error Accumulation" |

### 3.3 别名映射

`data/aliases.json` 存储预定义别名：

```json
{
  "Chain-of-Thought Reasoning": ["Chain-of-Thought", "CoT Reasoning"],
  "Error Accumulation in CoT": ["Error Accumulation", "CoT Error Propagation"]
}
```

---

## 4. Taxonomy 节点

```python
class TaxonomyNode(DataPoint):
    name: str
    description: str = ""
    node_type: str = "method_category"  # method_category | problem_category | leaf
    level: int = 0  # 0=root, 1=category, 2=subcategory, ...
    children: List[str] = []  # 子节点名称列表
    source_methods: List[str] = []  # 来源方法名称
    source_problems: List[str] = []  # 来源问题名称
    metadata: dict = {"index_fields": ["name", "description"]}
```

用于递归分类树的存储，不作为核心提取实体。
