"""
Integration test for the research cognitive graph pipeline.

Usage:
    EMBEDDING_PROVIDER=fastembed EMBEDDING_MODEL=BAAI/bge-small-en-v1.5 \
    EMBEDDING_DIMENSIONS=384 LLM_API_KEY=sk-xxx \
    /home/cuizhixing/cognee-env/bin/python -m pytest tests/test_pipeline.py -v

This test uses a single paper for validation (as per spec).
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest

pytestmark = pytest.mark.asyncio

TEST_PAPER = "/home/cuizhixing/.openclaw/workspace/科研内容/论文仓库/05_LLM工具与智能体记忆/2601.01982.pdf"


class TestM1Parsing:
    """M1.1 GROBID client tests."""

    async def test_grobid_alive(self):
        from src.parsing.grobid_client import GrobidClient
        client = GrobidClient()
        assert client.url == "http://localhost:8070"

    async def test_parse_pdf(self):
        from src.parsing.grobid_client import GrobidClient
        client = GrobidClient()
        paper = client.parse_pdf(TEST_PAPER)
        assert paper.title
        assert paper.abstract
        assert len(paper.sections) >= 3
        assert len(paper.references) > 5
        print(f"Title: {paper.title}")
        print(f"Sections: {[s['heading'] for s in paper.sections]}")


class TestM1Ingestion:
    """M1.2 Cognee ingestion tests."""

    async def test_ingest_paper(self):
        from src.pipeline.ingest import ingest_paper
        result = await ingest_paper(TEST_PAPER)
        assert result["chunk_count"] >= 3
        assert result["paper_id"]
        assert result["dataset_name"]
        assert os.path.exists(result["text_path"])
        print(f"Chunks: {result['chunk_count']}, Dataset: {result['dataset_name']}")


class TestM2Models:
    """M2.1 DataPoint model tests."""

    async def test_model_instantiation(self):
        from src.models.academic_nodes import Paper, Method, Problem, Insight, Resource
        paper = Paper(
            title="Test Paper",
            authors=["Alice", "Bob"],
            year=2024,
            abstract="This is a test.",
        )
        method = Method(name="TestMethod", description="A test method.")
        problem = Problem(name="TestProblem", description="A test problem.")
        insight = Insight(statement="Tests work.", confidence="high")
        resource = Resource(name="TestDataset", resource_type="dataset")
        assert paper.title == "Test Paper"
        assert method.name == "TestMethod"


class TestM2Extraction:
    """M2.2 + M2.3 extraction pipeline tests (require LLM_API_KEY)."""

    async def test_prompts_render(self):
        from src.extraction.prompts import get_extraction_prompt, get_insight_prompt
        p1 = get_extraction_prompt("Some paper text here.")
        p2 = get_insight_prompt("Some results here.")
        assert "ENTITY TYPES" in p1
        assert "INSIGHT TYPES" in p2

    async def test_extraction_pipeline(self):
        import os
        if not os.getenv("LLM_API_KEY"):
            pytest.skip("LLM_API_KEY not set")

        from src.parsing.grobid_client import GrobidClient
        from src.extraction.pipeline import AcademicExtractor
        from src.resolution.resolver import EntityResolver

        client = GrobidClient()
        paper = client.parse_pdf(TEST_PAPER)

        extractor = AcademicExtractor(resolver=EntityResolver("data/aliases.json"))
        result = await extractor.extract(paper, "test_paper_id")

        assert len(result["methods"]) >= 1
        assert len(result["problems"]) >= 1
        assert result["insights"] >= 1
        print(f"Methods: {result['methods']}")
        print(f"Problems: {result['problems']}")
        print(f"Insights: {result['insights']}")


class TestM2Resolution:
    """M2.4 entity resolution tests."""

    async def test_alias_resolution(self):
        from src.resolution.resolver import EntityResolver
        resolver = EntityResolver("data/aliases.json")
        name = await resolver.resolve("low-rank adaptation", "method")
        assert name == "LoRA"

    async def test_batch_resolution(self):
        from src.resolution.resolver import EntityResolver
        resolver = EntityResolver("data/aliases.json")
        entities = {
            "methods": [{"name": "low-rank adaptation"}],
            "problems": [{"name": "machine translation"}],
            "resources": [],
        }
        result = await resolver.resolve_batch(entities)
        assert result["methods"][0]["name"] == "LoRA"
        assert result["problems"][0]["name"] == "Machine Translation"


class TestM3Citations:
    """M3.1 citation network tests."""

    async def test_build_citations_empty(self):
        from src.pipeline.citations import build_citations
        from src.parsing.grobid_client import GrobidClient

        client = GrobidClient()
        paper = client.parse_pdf(TEST_PAPER)
        result = await build_citations(paper, existing_papers=[])
        assert result["citations_created"] == 0
        assert result["unmatched"] == len(paper.references)


class TestM3Taxonomy:
    """M3.2 taxonomy builder tests."""

    async def test_method_tree_insufficient(self):
        from src.taxonomy.builder import TaxonomyBuilder
        from src.models.academic_nodes import Method

        async def fake_embed(text):
            return [0.1] * 384

        builder = TaxonomyBuilder(fake_embed)
        methods = [Method(name="M1"), Method(name="M2")]
        categories = await builder.build_method_tree(methods)
        assert categories == []

    async def test_problem_tree(self):
        from src.taxonomy.builder import build_problem_tree
        from src.models.academic_nodes import Problem

        p1 = Problem(name="A", description="Contains B")
        p2 = Problem(name="B", description="Something else")
        problems = [p1, p2]
        result = await build_problem_tree(problems)
        assert result[1].parent == p1
