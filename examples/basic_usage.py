"""Basic usage example for Cognee Research Graph."""
import asyncio
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.extraction.pipeline import AcademicExtractor
from src.resolution.resolver import EntityResolver
from src.parsing.grobid_client import GrobidClient


async def main():
    """Extract knowledge graph from a single paper."""

    # 1. Parse PDF
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "path/to/paper.pdf"
    client = GrobidClient()
    paper = client.parse_pdf(pdf_path)

    print(f"Title: {paper.title}")
    print(f"Authors: {', '.join(paper.authors)}")
    print(f"Sections: {len(paper.sections)}")

    # 2. Extract entities
    resolver = EntityResolver("data/aliases.json")
    extractor = AcademicExtractor(resolver=resolver)
    result = await extractor.extract(paper, paper_id="example")

    # 3. Print results
    print("\n=== Methods ===")
    for m in result.get("methods", []):
        print(f"  - {m['name']} ({m.get('type', 'method')})")

    print("\n=== Problems ===")
    for p in result.get("problems", []):
        print(f"  - {p['name']} ({p.get('level', 'task')})")

    print("\n=== Resources ===")
    for r in result.get("resources", []):
        print(f"  - {r['name']} ({r.get('type', 'dataset')})")

    print("\n=== Insights ===")
    for i in result.get("insights", []):
        print(f"  [{i.get('type', 'insight')}] {i.get('statement', '')[:80]}...")

    print("\n=== Relations ===")
    for rel in result.get("relations", [])[:5]:
        print(f"  {rel['subject_name']} --{rel['predicate']}--> {rel['object_name']}")


if __name__ == "__main__":
    asyncio.run(main())
