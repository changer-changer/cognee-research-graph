import asyncio
import hashlib
import os
import sys
sys.path.insert(0, '/home/cuizhixing/cognee-env/lib/python3.10/site-packages')

from typing import List, Optional, Dict
from cognee.infrastructure.engine import DataPoint
from cognee.api.v1.search import SearchType, search
from cognee.modules.engine.operations.setup import setup
import cognee

from src.parsing.grobid_client import GrobidClient, PaperStruct
from src.config import PAPERS_DIR


class PaperChunk(DataPoint):
    """论文分块节点 - Cognee会自动索引到向量库和关系库"""
    text: str
    paper_title: str
    section: str
    authors: List[str]
    year: Optional[int] = None
    metadata: Dict = {"index_fields": ["text", "paper_title"]}


async def ingest_paper(pdf_path: str) -> dict:
    """Parse PDF via GROBID and ingest into Cognee using standard add->cognify pipeline."""
    client = GrobidClient()
    paper = client.parse_pdf(pdf_path)

    paper_id = hashlib.sha256(paper.title.encode()).hexdigest()[:16]
    dataset_name = f"paper_{paper_id}"

    # Build a markdown representation of the paper
    lines = []
    lines.append(f"# {paper.title}")
    lines.append("")
    if paper.authors:
        lines.append(f"**Authors:** {', '.join(paper.authors)}")
    if paper.year:
        lines.append(f"**Year:** {paper.year}")
    if paper.venue:
        lines.append(f"**Venue:** {paper.venue}")
    if paper.doi:
        lines.append(f"**DOI:** {paper.doi}")
    lines.append("")
    lines.append("## Abstract")
    lines.append("")
    lines.append(paper.abstract)
    lines.append("")

    for sec in paper.sections:
        lines.append(f"## {sec['heading']}")
        lines.append("")
        lines.append(sec["text"])
        lines.append("")

    paper_text = "\n".join(lines)

    # Save to file for Cognee ingestion
    os.makedirs(PAPERS_DIR, exist_ok=True)
    text_path = os.path.join(PAPERS_DIR, f"{paper_id}.md")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(paper_text)

    # Standard Cognee workflow: add -> cognify
    await cognee.add(text_path, dataset_name=dataset_name)
    await cognee.cognify(datasets=[dataset_name])

    return {
        "paper_id": paper_id,
        "paper_struct": paper,
        "chunk_count": len(paper.sections) + 1,  # sections + abstract
        "dataset_name": dataset_name,
        "text_path": text_path,
    }


async def verify_ingestion(paper_title: str) -> bool:
    """Quick verification that chunks are searchable."""
    results = await search(
        query_type=SearchType.CHUNKS,
        query_text="introduction",
    )
    if results:
        for r in results:
            if paper_title.lower() in str(r).lower():
                return True
    return False
