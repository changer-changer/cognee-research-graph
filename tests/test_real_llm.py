"""Test M2.3 with real Kimi LLM API."""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio

TEST_PAPER = "/home/cuizhixing/.openclaw/workspace/科研内容/论文仓库/05_LLM工具与智能体记忆/2601.01982.pdf"


async def test_real_extraction():
    from src.parsing.grobid_client import GrobidClient
    from src.extraction.pipeline import AcademicExtractor
    from src.resolution.resolver import EntityResolver

    print("Parsing PDF...")
    client = GrobidClient()
    paper = client.parse_pdf(TEST_PAPER)
    print(f"Title: {paper.title}")
    print(f"Sections: {len(paper.sections)}")

    print("\nRunning extraction pipeline with real LLM...")
    extractor = AcademicExtractor(resolver=EntityResolver("data/aliases.json"))
    result = await extractor.extract(paper, "test_real_001")

    print(f"\n--- Results ---")
    print(f"Methods ({len(result['methods'])}): {result['methods']}")
    print(f"Problems ({len(result['problems'])}): {result['problems']}")
    print(f"Insights: {result['insights']}")
    print(f"Relations: {result['relations']}")

    assert len(result["methods"]) >= 1, "Expected at least 1 method"
    assert len(result["problems"]) >= 1, "Expected at least 1 problem"
    assert result["insights"] >= 1, "Expected at least 1 insight"

    print("\nReal LLM extraction test PASSED!")
    return True


if __name__ == "__main__":
    ok = asyncio.run(test_real_extraction())
    print(f"\nM2.3 Real LLM test: {'PASS' if ok else 'FAIL'}")
