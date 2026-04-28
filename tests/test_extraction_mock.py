"""Test M2.3 extraction pipeline with mock LLM (no API key needed)."""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio
from src.extraction.pipeline import AcademicExtractor, SimpleLLMClient
from src.parsing.grobid_client import PaperStruct


class MockLLMClient:
    """Returns deterministic JSON responses for testing."""

    async def complete(self, prompt: str, temperature: float = 0.3, max_tokens: int = 4096) -> str:
        if "ENTITY TYPES" in prompt:
            return """{
                "entities": {
                    "methods": [
                        {"name": "low-rank adaptation", "description": "A parameter-efficient fine-tuning method", "type": "fine_tuning"}
                    ],
                    "problems": [
                        {"name": "machine translation", "description": "Translating text between languages", "level": "task"}
                    ],
                    "resources": [
                        {"name": "WMT-14", "type": "dataset"}
                    ]
                },
                "relations": [
                    {"subject_name": "ChaosBench", "subject_type": "Paper", "predicate": "proposes", "object_name": "low-rank adaptation", "object_type": "Method"},
                    {"subject_name": "low-rank adaptation", "subject_type": "Method", "predicate": "solves", "object_name": "machine translation", "object_type": "Problem"}
                ]
            }"""
        else:
            return """{
                "insights": [
                    {"statement": "LoRA reduces parameters by 1000x", "type": "empirical_finding", "confidence": "high", "evidence_quote": "Table 1 shows..."}
                ]
            }"""


async def test_extraction_pipeline():
    from src.resolution.resolver import EntityResolver

    paper = PaperStruct(
        title="Test Paper on LoRA",
        authors=["Alice"],
        abstract="We propose LoRA for efficient fine-tuning.",
        year=2024,
        venue="ICML",
        sections=[
            {"heading": "Introduction", "text": "We propose low-rank adaptation."},
            {"heading": "Methods", "text": "Our method uses LoRA."},
            {"heading": "Experiments", "text": "We test on machine translation."},
        ],
        references=[],
    )

    extractor = AcademicExtractor(
        llm_client=MockLLMClient(),
        resolver=EntityResolver("data/aliases.json"),
    )

    result = await extractor.extract(paper, "test_paper_001")

    print(f"Methods: {result['methods']}")
    print(f"Problems: {result['problems']}")
    print(f"Insights: {result['insights']}")
    print(f"Relations: {result['relations']}")

    assert "LoRA" in result["methods"], f"Expected LoRA in methods, got {result['methods']}"
    assert "Machine Translation" in result["problems"], f"Expected Machine Translation in problems"
    assert result["insights"] >= 1, f"Expected >=1 insights"
    assert result["relations"] >= 1, f"Expected >=1 relations"

    print("\nAll M2.3 extraction checks passed!")
    return True


if __name__ == "__main__":
    ok = asyncio.run(test_extraction_pipeline())
    print(f"M2.3 Mock extraction test: {'PASS' if ok else 'FAIL'}")
