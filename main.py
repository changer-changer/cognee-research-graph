import asyncio
import sys
import os

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pipeline.ingest import ingest_paper
from src.extraction.pipeline import AcademicExtractor
from src.resolution.resolver import EntityResolver
from src.pipeline.citations import build_citations
from src.taxonomy.builder import TaxonomyBuilder


async def main(pdf_path: str):
    if not os.path.exists(pdf_path):
        print(f"Error: file not found: {pdf_path}")
        sys.exit(1)

    print("=" * 60)
    print("Research Cognitive Graph System - Pipeline")
    print("=" * 60)

    # 1. Ingest
    print("\n[Step 1] Ingesting PDF into Cognee...")
    result = await ingest_paper(pdf_path)
    paper_id = result["paper_id"]
    paper_struct = result["paper_struct"]
    print(f"  Paper ID: {paper_id}")
    print(f"  Title: {paper_struct.title}")
    print(f"  Chunks created: {result['chunk_count']}")

    # 2. Academic extraction
    print("\n[Step 2] Extracting academic entities...")
    resolver = EntityResolver("data/aliases.json")
    extractor = AcademicExtractor(resolver=resolver)
    try:
        extraction = await extractor.extract(paper_struct, paper_id)
        print(f"  Methods: {extraction['methods']}")
        print(f"  Problems: {extraction['problems']}")
        print(f"  Insights: {extraction['insights']}")
        print(f"  Relations: {extraction['relations']}")
    except Exception as e:
        print(f"  Extraction failed: {e}")
        import traceback
        traceback.print_exc()

    # 3. Citations
    print("\n[Step 3] Building citation network...")
    try:
        citation_result = await build_citations(paper_struct, existing_papers=[])
        print(f"  Citations created: {citation_result['citations_created']}")
        print(f"  Unmatched references: {citation_result['unmatched']}")
    except Exception as e:
        print(f"  Citation extraction skipped: {e}")

    # 4. Taxonomy
    print("\n[Step 4] Building taxonomy...")
    # Taxonomy requires prior extraction to have populated method/problem nodes;
    # for a single-paper run it is mostly a no-op.
    print("  (Skipped for single-paper run; taxonomy requires multi-paper corpus)")

    print("\n" + "=" * 60)
    print("Pipeline complete. Use cognee.search() to query the graph.")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py path/to/paper.pdf")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
