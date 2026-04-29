# Cognee Research Graph

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Turn academic papers into structured knowledge graphs.**
>
> Extract methods, problems, resources, and insights from research papers using staged LLM pipelines.

## What is this?

Cognee Research Graph is a domain-specific knowledge extraction system built on top of [Cognee](https://github.com/topoteretes/cognee). It transforms academic papers into structured knowledge graphs with hierarchical relationships between methods and problems.

### Key Features

- **3-Stage Extraction Pipeline**: Top-level entities → Sub-methods → Insights
- **Hierarchical Method Trees**: `DIFFCOT contains Step-level Forward Noising contains Reward-ranked Candidates`
- **Problem Taxonomy**: Task → Challenge → Sub-challenge with `is_subtask_of`
- **Entity Resolution**: Acronym matching + Jaccard similarity deduplication
- **Recursive Taxonomy Builder**: LLM-powered bottom-up category summarization
- **Multi-Model Support**: OpenAI, Anthropic, Kimi Code API

## Quick Start

```bash
# Clone
git clone https://github.com/changer-changer/cognee-research-graph.git
cd cognee-research-graph

# Install
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run on a paper
python main.py path/to/paper.pdf
```

## Architecture

```
PDF → GROBID → Structured Text → Stage 1a (Top-level) → Stage 1b (Sub-methods) → Stage 2 (Insights)
                                            ↓                    ↓                    ↓
                                    Method/Problem/Resource    Method Hierarchy      Insight Association
                                            ↓
                                    Entity Resolution (Deduplication)
                                            ↓
                                    Cognee Graph DB (Kuzu) + Vector DB (LanceDB)
                                            ↓
                                    Recursive Taxonomy Builder
```

## Pipeline Stages

### Stage 1a: Top-Level Extraction
Extracts from Introduction + Method sections:
- **Methods**: Top-level framework (e.g., DIFFCOT)
- **Problems**: Task (Chain-of-Thought Reasoning) + Challenge (Error Accumulation)
- **Resources**: Datasets (MATH-1, SVAMP), benchmarks

### Stage 1b: Sub-Method Extraction
Deep-dive into Method section:
- Techniques (Diffusion Sliding-Window Mechanism)
- Components (Reward-ranked Candidate Collection)
- Hierarchical `contains` relationships

### Stage 2: Insight Extraction
From Experiments + Results:
- Empirical findings
- Method innovations
- Boundary conditions
- Evidence-backed claims with paper quotes

## Example Output

### Methods
```
DIFFCOT (method)
├── Step-level Forward Noising (technique)
│   └── Reward-ranked Candidate Collection (component)
├── Diffusion Sliding-Window Mechanism (technique)
└── Causal Diffusion Noise (technique)
```

### Problems
```
Chain-of-Thought Reasoning (task)
├── Error Accumulation in CoT (challenge)
└── Exposure Bias in CoT (challenge)
```

### Insights
| Type | Statement |
|------|-----------|
| boundary_condition | Self-verification methods are unstable across models and datasets |
| empirical_finding | Local step-wise optimization alone is insufficient for stable reasoning |
| method_innovation | Iterative denoising provides more robust CoT than self-verification |

## Configuration

Set your LLM API key:

```bash
# Option 1: Anthropic-compatible (Kimi Code)
export ANTHROPIC_AUTH_TOKEN=your_token
export ANTHROPIC_BASE_URL=https://api.kimi.com/coding/

# Option 2: OpenAI-compatible
export OPENAI_API_KEY=your_key
```

## Project Structure

```
src/
├── extraction/
│   ├── prompts.py          # Stage 1a/1b/2 LLM prompts
│   └── pipeline.py         # AcademicExtractor with staged extraction
├── models/
│   └── academic_nodes.py   # Paper, Method, Problem, Insight, Resource
├── resolution/
│   └── resolver.py         # Entity deduplication & normalization
├── taxonomy/
│   └── builder.py          # Recursive LLM taxonomy builder
└── parsing/
    └── grobid_client.py    # GROBID PDF parser client
```

## Testing

```bash
# Run comprehensive pipeline test
python tests/comprehensive_pipeline_test.py

# Outputs saved to tests/output/
# 01_pdf_to_markdown.md
# 03_stage1a_raw_extraction.json
# 04_stage1b_raw_extraction.json
# 05_stage2_raw_insights.json
# 07_database_contents.txt
```

## Distribution

Want a self-contained package with modified Cognee included?

```bash
./build_distribution.sh
# Produces: cognee-research-graph-YYYYMMDD.tar.gz
```

## Cognee Modifications

This project includes a modified Cognee v1.0.3:
- `cognee/__init__.py`: Clears proxy env vars to avoid SOCKS conflicts

## Limitations

- Training objectives (DPO Loss Adaptation, Hybrid Prefix) not fully extracted due to context limits
- Multi-paper taxonomy intermediate layers not yet validated (needs 10+ papers)
- Requires GROBID running at `http://localhost:8070`

## License

MIT License — see [LICENSE](LICENSE) file.

## Acknowledgments

Built on [Cognee](https://github.com/topoteretes/cognee) by Topoteretes.
