"""Manual test runner (avoids ROS2 pytest plugin conflicts)."""

import sys
import os
import asyncio
import traceback

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

TEST_PAPER = "/home/cuizhixing/.openclaw/workspace/科研内容/论文仓库/05_LLM工具与智能体记忆/2601.01982.pdf"

results = []


def report(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    results.append((name, ok, detail))
    print(f"  [{status}] {name}")
    if detail and not ok:
        print(f"         {detail}")


async def run_all():
    print("=" * 60)
    print("Research Cognitive Graph - Module Tests")
    print("=" * 60)

    # M1.1 GROBID parsing
    print("\n[M1.1] GROBID Client")
    try:
        from src.parsing.grobid_client import GrobidClient
        client = GrobidClient()
        paper = client.parse_pdf(TEST_PAPER)
        report("grobid_alive", True)
        report("title_non_empty", bool(paper.title), f"title='{paper.title}'")
        report("abstract_non_empty", bool(paper.abstract), f"len={len(paper.abstract)}")
        report("sections_>=3", len(paper.sections) >= 3, f"count={len(paper.sections)}")
        report("references_>5", len(paper.references) > 5, f"count={len(paper.references)}")
        print(f"       Title: {paper.title}")
        print(f"       Sections: {[s['heading'] for s in paper.sections[:6]]}")
    except Exception as e:
        report("grobid_alive", False, str(e))
        traceback.print_exc()

    # M1.2 Ingestion
    print("\n[M1.2] Cognee Ingestion")
    try:
        from src.pipeline.ingest import ingest_paper
        result = await ingest_paper(TEST_PAPER)
        report("ingest_success", True)
        report("chunk_count_>=3", result["chunk_count"] >= 3, f"count={result['chunk_count']}")
        report("dataset_created", bool(result["dataset_name"]))
        report("text_file_exists", os.path.exists(result["text_path"]))
    except Exception as e:
        report("ingest_success", False, str(e))
        traceback.print_exc()

    # M2.1 Models
    print("\n[M2.1] Academic DataPoint Models")
    try:
        from src.models.academic_nodes import Paper, Method, Problem, Insight, Resource
        p = Paper(title="T", authors=["A"], year=2024, abstract="...")
        m = Method(name="M", description="...")
        pr = Problem(name="P", description="...")
        i = Insight(statement="I", confidence="high")
        r = Resource(name="R", resource_type="dataset")
        report("paper_model", p.title == "T")
        report("method_model", m.name == "M")
        report("problem_model", pr.name == "P")
        report("insight_model", i.confidence == "high")
        report("resource_model", r.resource_type == "dataset")
    except Exception as e:
        report("models", False, str(e))
        traceback.print_exc()

    # M2.2 Prompts
    print("\n[M2.2] Extraction Prompts")
    try:
        from src.extraction.prompts import get_extraction_prompt, get_insight_prompt
        p1 = get_extraction_prompt("text")
        p2 = get_insight_prompt("text")
        report("extraction_prompt", "ENTITY TYPES" in p1)
        report("insight_prompt", "INSIGHT TYPES" in p2)
    except Exception as e:
        report("prompts", False, str(e))
        traceback.print_exc()

    # M2.3 Extraction Pipeline (requires LLM key)
    print("\n[M2.3] Academic Extraction Pipeline")
    if not os.getenv("LLM_API_KEY"):
        report("extraction_llm", False, "LLM_API_KEY not set (set it to run this test)")
    else:
        try:
            from src.parsing.grobid_client import GrobidClient
            from src.extraction.pipeline import AcademicExtractor
            from src.resolution.resolver import EntityResolver
            client = GrobidClient()
            paper = client.parse_pdf(TEST_PAPER)
            extractor = AcademicExtractor(resolver=EntityResolver("data/aliases.json"))
            result = await extractor.extract(paper, "test_id")
            report("methods_>=1", len(result["methods"]) >= 1, str(result["methods"]))
            report("problems_>=1", len(result["problems"]) >= 1, str(result["problems"]))
            report("insights_>=1", result["insights"] >= 1, str(result["insights"]))
        except Exception as e:
            report("extraction", False, str(e))
            traceback.print_exc()

    # M2.4 Resolution
    print("\n[M2.4] Entity Resolution")
    try:
        from src.resolution.resolver import EntityResolver
        resolver = EntityResolver("data/aliases.json")
        name = await resolver.resolve("low-rank adaptation", "method")
        report("alias_lora", name == "LoRA", f"got='{name}'")

        entities = {
            "methods": [{"name": "low-rank adaptation"}],
            "problems": [{"name": "machine translation"}],
            "resources": [],
        }
        result = await resolver.resolve_batch(entities)
        report("batch_methods", result["methods"][0]["name"] == "LoRA")
        report("batch_problems", result["problems"][0]["name"] == "Machine Translation")
    except Exception as e:
        report("resolution", False, str(e))
        traceback.print_exc()

    # M3.1 Citations
    print("\n[M3.1] Citation Network")
    try:
        from src.pipeline.citations import build_citations
        from src.parsing.grobid_client import GrobidClient
        client = GrobidClient()
        paper = client.parse_pdf(TEST_PAPER)
        result = await build_citations(paper, existing_papers=[])
        report("citations_empty", result["citations_created"] == 0)
        report("unmatched_refs", result["unmatched"] == len(paper.references))
    except Exception as e:
        report("citations", False, str(e))
        traceback.print_exc()

    # M3.2 Taxonomy
    print("\n[M3.2] Taxonomy Builder")
    try:
        from src.taxonomy.builder import TaxonomyBuilder, build_problem_tree
        from src.models.academic_nodes import Method, Problem

        async def fake_embed(text):
            return [0.1] * 384

        builder = TaxonomyBuilder(fake_embed)
        cats = await builder.build_method_tree([Method(name="M1"), Method(name="M2")])
        report("method_tree_skip", cats == [])

        p1 = Problem(name="A", description="Contains B")
        p2 = Problem(name="B", description="Something else")
        probs = await build_problem_tree([p1, p2])
        report("problem_tree", probs[1].parent == p1)
    except Exception as e:
        report("taxonomy", False, str(e))
        traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("All checks passed!")
    else:
        print("Some checks failed. See details above.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all())
