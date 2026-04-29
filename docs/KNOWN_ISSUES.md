# 已知问题与限制 (Known Issues & Limitations)

> 本文档记录所有已知问题、限制和未来优化方向。

---

## 1. 提取精度限制

### 1.1 训练方法未完全提取

**问题**: §3.4 的 DPO Loss Adaptation、Hybrid Prefix Construction、MCTS-based Trajectory Construction 等训练目标相关方法未被 LLM 提取。

**原因**: Prompt 输入截断在 8000 字符，Method 部分内容优先覆盖核心架构，训练细节被截断。

**影响**: 中等。训练方法对复现论文很重要，但对理解论文核心贡献影响较小。

**潜在解决方案**:
- 将 Method 部分输入扩展到 12000+ 字符
- 增加专门提取训练目标的 Stage 1c
- 在 Prompt 中增加 few-shot 示例包含训练目标

---

### 1.2 评估指标未提取

**问题**: accuracy、BLEU、ROUGE 等评估指标未出现在 Resource 中。

**原因**: Resource 定义聚焦 datasets/benchmarks，metrics 的定义边界模糊。

**影响**: 低。

**潜在解决方案**:
- 在 Resource type 中增加 `metric` 类型
- 在 Stage 1a Prompt 中明确提示提取评估指标

---

### 1.3 论文类型覆盖不全

**问题**: 仅测试了方法论文 (Method Paper)。Survey、Benchmark、Analysis 类型的提取效果未知。

**原因**: Survey 论文没有单一 top-level method，Benchmark 论文的方法结构不同。

**影响**: 高。限制了系统的通用性。

**潜在解决方案**:
- 为 Survey 论文设计专门的提取 Prompt（提取 review 框架而非单一方法）
- 为 Benchmark 论文设计提取 Prompt（提取评估维度而非方法层级）

---

## 2. Taxonomy 限制

### 2.1 多论文中间层未验证

**问题**: 当前单论文仅 5 个方法节点，LLM 直接汇总为单根。当 10+ 方法时，递归树应生成中间层级，但未验证。

**原因**: 缺乏多论文测试数据。

**影响**: 中等。Taxonomy Builder 的核心逻辑已验证，但大规模场景效果未知。

**潜在解决方案**:
- 批量处理 10-20 篇论文
- 观察中间层是否合理
- 调整聚类参数（当前 3-5 个节点/组）

---

### 2.2 Problem 树层级浅

**问题**: 当前 Problem 树仅 3 个叶子节点，未验证更深层级（task → challenge → sub_challenge → sub_sub_challenge）。

**原因**: 单论文的问题数量有限。

**影响**: 低。

---

## 3. 架构限制

### 3.1 Cognee 版本绑定

**问题**: 使用 Cognee 内部 API（`add_data_points`、`DataPoint`），升级 Cognee 时可能中断。

**当前版本**: 1.0.3

**影响**: 高。无法享受 Cognee  upstream 的新功能和 bug 修复。

**缓解措施**:
- 锁定版本 `pip install cognee==1.0.3`
- 分发包包含完整 Cognee 源码
- 升级时手动 cherry-pick

**长期方案**:
- 向 Cognee 社区贡献扩展点（plugin/extension API）
- 或完全 fork 并独立维护

---

### 3.2 单线程处理

**问题**: 当前 Pipeline 是顺序执行（1a → 1b → 2 → resolution → store），未并行化。

**原因**: Stage 2 依赖 Stage 1 的实体列表，天然串行。

**影响**: 低。单论文处理时间 55-110s 已可接受。

**潜在优化**:
- Stage 1a 和 1b 可以并行（1b 需要 top_level_method，但可以从 1a 的部分输出触发）
- 多论文批量处理时可以并行

---

### 3.3 缺乏持久化缓存

**问题**: 每次重新运行都重新调用 LLM，即使论文已处理过。

**原因**: 无中间结果缓存机制。

**影响**: 中等。重复运行浪费 Token。

**潜在解决方案**:
- 按论文标题哈希缓存 Stage 1/2 的原始 JSON 输出
- 缓存位置：`data/cache/{paper_hash}_stage1a.json`

---

## 4. LLM 依赖限制

### 4.1 模型一致性

**问题**: 仅测试了 Anthropic (Kimi Code) API。OpenAI、Moonshot 等模型的输出格式一致性未验证。

**原因**: 不同模型的 JSON 遵循能力不同。

**影响**: 中等。

**缓解措施**:
- `_safe_parse_json` 函数处理 JSON 解析容错
- 建议使用 Claude/GPT-4 级别模型

---

### 4.2 长论文截断

**问题**: Method 部分超过 8000 字符时截断，可能丢失尾部内容。

**原因**: LLM 上下文窗口和成本限制。

**影响**: 中等。

**潜在解决方案**:
- 使用支持长上下文的模型（Claude 200K, GPT-4 128K）
- 智能文本选择：优先保留 §3.x 小节，截断 §2 Background

---

## 5. GROBID 依赖

### 5.1 需要本地 GROBID 服务

**问题**: 必须运行 `docker run -p 8070:8070 lfoppiano/grobid:0.8.0`，增加了部署复杂度。

**影响**: 中等。

**潜在解决方案**:
- 支持直接解析 Markdown/TeX 源码
- 集成其他 PDF 解析器（PyMuPDF, pdfplumber）作为 fallback
- 提供在线 GROBID 实例选项

---

## 6. 功能缺失

### 6.1 无 Web UI

**问题**: 纯命令行工具，非技术用户难以使用。

**影响**: 高。限制了用户群体。

**潜在解决方案**:
- Streamlit 界面：上传 PDF → 查看知识图谱
- 集成可视化库（pyvis, networkx + d3.js）

---

### 6.2 无 API 服务

**问题**: 无法作为服务被其他系统调用。

**影响**: 中等。

**潜在解决方案**:
- FastAPI 封装
- 异步任务队列（Celery + Redis）

---

### 6.3 无多语言支持

**问题**: Prompt 和提取逻辑均为英文，中文论文效果未知。

**影响**: 高（对中文用户）。

**潜在解决方案**:
- 多语言 Prompt 模板
- 在 Prompt 中明确允许混合语言输出

---

## 7. 优化方向优先级

| 优先级 | 方向 | 难度 | 影响力 |
|--------|------|------|--------|
| P0 | 训练方法提取 | 低 | 高 |
| P0 | 多论文批量测试 | 低 | 高 |
| P1 | Web UI (Streamlit) | 中 | 高 |
| P1 | 持久化缓存 | 低 | 中 |
| P1 | Survey/Benchmark 支持 | 中 | 高 |
| P2 | API 服务 (FastAPI) | 中 | 中 |
| P2 | 多语言支持 | 中 | 高 |
| P2 | Docker 一键部署 | 低 | 中 |
| P3 | Cognee 版本解耦 | 高 | 低 |
| P3 | PyPI 发布 | 中 | 低 |
