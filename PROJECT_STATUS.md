# 科研认知图谱系统 - 项目状态

**记录日期**: 2026-04-29
**项目路径**: /home/cuizhixing/research_graph
**代码规模**: ~1,542 行源码 + ~3,187 行测试

---

## 已完成的组件（确认可用）

### 1. PDF 解析层
| 组件 | 文件 | 状态 |
|------|------|------|
| GROBID 客户端 | `src/parsing/grobid_client.py` | 可用。解析 15+ sections，提取标题/作者/摘要/章节 |

### 2. LLM 提取层（核心）
| 组件 | 文件 | 状态 |
|------|------|------|
| Stage 1a Prompt | `src/extraction/prompts.py:EXTRACTION_PROMPT_1A` | 可用。元数据注入 + 顶层实体提取 |
| Stage 1b Prompt | `src/extraction/prompts.py:EXTRACTION_PROMPT_1B` | 可用。子方法层级提取 |
| Stage 2 Prompt | `src/extraction/prompts.py:INSIGHT_PROMPT_V2` | 可用。洞察提取 + 实体关联 |
| Prompt 生成器 | `src/extraction/prompts.py:get_*_prompt_*` | 可用。三段式参数化生成 |
| 提取管道 | `src/extraction/pipeline.py:AcademicExtractor` | 可用。staged extraction (1a→1b→2) |
| JSON 安全解析 | `src/extraction/pipeline.py:_safe_parse_json` | 可用。容错解析 LLM 输出 |

### 3. 数据模型层
| 组件 | 文件 | 状态 |
|------|------|------|
| Paper | `src/models/academic_nodes.py` | 可用 |
| Method | `src/models/academic_nodes.py` | 可用。含 contains/uses_technique 关系 |
| Problem | `src/models/academic_nodes.py` | 可用。含 is_subtask_of 关系 |
| Resource | `src/models/academic_nodes.py` | 可用。数据集/基准 |
| Insight | `src/models/academic_nodes.py` | 可用。含 from_paper + related_* |
| MethodRelations | `src/models/academic_nodes.py` | 可用。显式存储方法关系边 |
| PaperRelations | `src/models/academic_nodes.py` | 可用。显式存储论文关系边 |
| ProblemRelations | `src/models/academic_nodes.py` | 可用。显式存储问题层级边 |

### 4. 实体归一化层
| 组件 | 文件 | 状态 |
|------|------|------|
| 实体解析器 | `src/resolution/resolver.py:EntityResolver` | 可用。别名映射 + LLM 辅助 |
| 批次内去重 | `src/resolution/resolver.py:_dedup_batch` | 可用。缩写匹配 + Jaccard 相似度 |
| 同实体判断 | `src/resolution/resolver.py:_is_same_entity` | 可用。多策略融合 |

### 5. 分类树层
| 组件 | 文件 | 状态 |
|------|------|------|
| TaxonomyNode | `src/taxonomy/builder.py` | 可用。树节点 DataPoint |
| 递归构建器 | `src/taxonomy/builder.py:RecursiveTaxonomyBuilder` | 可用。自底向上 LLM 总结 |
| 方法树构建 | `src/taxonomy/builder.py:build_method_tree` | 可用 |
| 问题树构建 | `src/taxonomy/builder.py:build_problem_tree` | 可用 |

### 6. 存储层（基于 Cognee）
| 组件 | 状态 |
|------|------|
| Kuzu 图数据库 | 可用。节点/边写入正常 |
| LanceDB 向量存储 | 可用。Taxonomy embedding 正常 |
| DataPoint 写入 | 可用。add_data_points 成功 |
| 数据库清理 | 可用。prune_data + prune_system |

---

## 验证结果（DIFFCOT 论文）

### 提取精度
| 指标 | 数值 | 质量 |
|------|------|------|
| Top-level Methods | 1 | DIFFCOT（唯一顶层方法） |
| Sub-methods | 4 | Step-level Forward Noising / Diffusion Sliding-Window / Causal Diffusion Noise / Reward-ranked Candidate Collection |
| Problems | 3 | Chain-of-Thought Reasoning(task) / Error Accumulation(challenge) / Exposure Bias(challenge) |
| Resources | 2 | MATH-1 / SVAMP（仅数据集，无模型混入） |
| Insights | 3 | 全部有证据引用，精确关联实体 |
| Relations | 9 | 无悬空，全部使用真实论文标题 |

### 数据库质量
| 检查项 | 结果 |
|--------|------|
| 空节点名称 | 0 个 |
| 重复节点 | 0 个 |
| "this_paper" 悬空关系 | 0 条 |
| Related Work 污染 | 无 |
| 模型误分类为资源 | 无 |

### Taxonomy 树
| 树 | 根节点 | 叶子数 |
|----|--------|--------|
| Method Tree | Diffusion-based Chain-of-Thought Reasoning | 5 |
| Problem Tree | Chain-of-Thought Failure Modes | 3 |

---

## 已知限制

1. **训练方法未完全提取**: §3.4 的 DPO Loss Adaptation、Hybrid Prefix Construction 等训练目标相关方法仍未被 LLM 提取。原因：prompt 输入截断在 8000 字符，Method 部分内容优先覆盖核心架构，训练细节被截断。

2. **多论文 Taxonomy 中间层未验证**: 当前单论文仅 5 个方法节点，LLM 直接汇总为单根。当 10+ 方法时，递归树应生成中间层级，但尚未验证。

3. **Resource 提取偏少**: 仅提取 2 个数据集。论文中还使用了 Qwen3-8B、LLaMA 等模型作为实验对象，但根据规则被正确归类为 Method 而非 Resource。评估指标（accuracy）未提取。

4. **Insight 类型覆盖**: 当前 3 条 insight 均为 empirical_finding / method_innovation / boundary_condition。未触发 negative_result 或 theoretical_claim 类型。

---

## 架构决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 删除 Paper Type 检测 | 是 | 避免类型偏见导致的提取策略偏差 |
| 三阶段分离 (1a→1b→2) | 是 | 降低单 prompt 复杂度，提高提取精度 |
| 元数据注入 prompt 头部 | 是 | 强制 LLM 使用真实论文标题，消除 "this_paper" |
| MethodRelations/PaperRelations/ProblemRelations | 是 | Cognee DataPoint 模型不能直接表达关系边，需显式容器节点 |
| 预训练模型 = Method 而非 Resource | 是 | 避免资源列表膨胀，保持 Resource 语义纯净 |
| 数量不限 | 是 | 用户明确要求 "数量不要局限" |

---

## 文件清单

### 核心源码
```
src/
├── parsing/
│   └── grobid_client.py          # GROBID PDF 解析
├── extraction/
│   ├── prompts.py                # 三阶段 LLM Prompt
│   └── pipeline.py               # AcademicExtractor 管道
├── models/
│   └── academic_nodes.py         # DataPoint 模型定义
├── resolution/
│   └── resolver.py               # 实体归一化与去重
├── taxonomy/
│   └── builder.py                # 递归分类树构建
└── config.py                     # 配置
```

### 测试与输出
```
tests/
├── comprehensive_pipeline_test.py    # 主测试：9 阶段全流程
├── output/
│   ├── 01_pdf_to_markdown.md       # GROBID 解析结果
│   ├── 03_stage1a_raw_extraction.json
│   ├── 04_stage1b_raw_extraction.json
│   ├── 05_stage2_raw_insights.json
│   ├── 06_normalized_entities.json
│   ├── 07_database_contents.txt    # DB 内容验证
│   ├── 08_taxonomy_results.txt     # 分类树结果
│   └── OPTIMIZATION_LOG.md         # 优化日志（4 轮）
└── [其他测试文件...]
```

---

## 下一步（待定）

1. **增加文本输入长度**: 将 Method 部分输入从 8000 字符扩展到 12000+，尝试提取训练目标相关子方法
2. **多论文批量测试**: 验证 3-5 篇不同领域论文的提取效果，测试 Taxonomy 中间层生成
3. **评估指标提取**: 在 Resource 中增加 evaluation metrics（accuracy, BLEU, ROUGE 等）
4. **Problem 中间层级**: 当前 Problem 树仅 3 个叶子，增加更多论文后验证递归分组效果
