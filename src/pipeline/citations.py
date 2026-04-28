import json
import os
import sys
sys.path.insert(0, '/home/cuizhixing/cognee-env/lib/python3.10/site-packages')

from typing import List
from cognee.infrastructure.engine import DataPoint
from cognee.tasks.storage import add_data_points

from src.parsing.grobid_client import PaperStruct
from src.config import UNMATCHED_CITATIONS_PATH


class CitationEdge(DataPoint):
    """引用关系容器"""
    from_paper_title: str
    to_paper_title: str
    citation_context: str = ""
    metadata: dict = {}


async def build_citations(paper_struct: PaperStruct, existing_papers: List[str]) -> dict:
    """
    paper_struct: GROBID解析结果
    existing_papers: 库中已有论文的标题列表
    """
    citations = []
    unmatched = []

    for ref in paper_struct.references:
        ref_title = ref.get("title", "")
        if not ref_title:
            unmatched.append(ref)
            continue

        matched = None
        ref_clean = ref_title.lower().strip().rstrip(".")
        for existing in existing_papers:
            if ref_clean == existing.lower().strip().rstrip("."):
                matched = existing
                break

        if matched:
            edge = CitationEdge(
                from_paper_title=paper_struct.title,
                to_paper_title=matched,
            )
            citations.append(edge)
        else:
            for existing in existing_papers:
                if ref_clean in existing.lower() or existing.lower() in ref_clean:
                    edge = CitationEdge(
                        from_paper_title=paper_struct.title,
                        to_paper_title=existing,
                    )
                    citations.append(edge)
                    matched = existing
                    break

        if not matched:
            unmatched.append(ref)

    if citations:
        await add_data_points(citations)

    # Persist unmatched citations
    if unmatched:
        os.makedirs(os.path.dirname(UNMATCHED_CITATIONS_PATH) or ".", exist_ok=True)
        with open(UNMATCHED_CITATIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(unmatched, f, indent=2, ensure_ascii=False)

    return {
        "citations_created": len(citations),
        "unmatched": len(unmatched),
    }
