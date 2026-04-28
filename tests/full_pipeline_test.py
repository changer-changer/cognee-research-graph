"""Full end-to-end pipeline test: parse -> extract -> verify DB contents."""
import sys, os, asyncio, json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, '/home/cuizhixing/cognee-env/lib/python3.10/site-packages')

TEST_PAPER = "/home/cuizhixing/.openclaw/workspace/科研内容/论文仓库/05_LLM工具与智能体记忆/2601.01982.pdf"


async def main():
    print("=" * 70)
    print("FULL PIPELINE TEST")
    print("=" * 70)

    # 0. Clean up previous data
    print("\n[0/5] Cleaning previous test data...")
    import cognee
    cognee.config.set_embedding_provider("fastembed")
    cognee.config.set_embedding_model("jinaai/jina-embeddings-v3")
    cognee.config.set_embedding_dimensions(1024)
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    # Also directly remove Kuzu DB and LanceDB since prune doesn't always clear them
    db_path = '/home/cuizhixing/cognee-env/lib/python3.10/site-packages/cognee/.cognee_system/databases/cognee_graph_kuzu'
    if os.path.exists(db_path):
        os.remove(db_path)
    lancedb_path = '/home/cuizhixing/cognee-env/lib/python3.10/site-packages/cognee/.cognee_system/databases/cognee.lancedb'
    if os.path.exists(lancedb_path):
        import shutil
        shutil.rmtree(lancedb_path)
    print("  ✅ Database cleaned")

    # 1. GROBID parse
    print("\n[1/5] GROBID Parsing...")
    from src.parsing.grobid_client import GrobidClient
    client = GrobidClient()
    paper = client.parse_pdf(TEST_PAPER)
    print(f"  Title: {paper.title[:80]}")
    print(f"  Sections: {len(paper.sections)}")
    print(f"  References: {len(paper.references)}")

    # 2. Extract with real LLM
    print("\n[2/5] LLM Extraction...")
    from src.extraction.pipeline import AcademicExtractor
    from src.resolution.resolver import EntityResolver
    extractor = AcademicExtractor(resolver=EntityResolver("data/aliases.json"))
    result = await extractor.extract(paper, "full_test_001")

    print(f"  Paper type: {result['paper_type']}")
    print(f"  Methods: {result['methods']}")
    print(f"  Problems: {result['problems']}")
    print(f"  Resources: {result['resources']}")
    print(f"  Insights: {result['insights']}")
    print(f"  Relations: {result['relations']}")

    # 3. Verify DB contents
    print("\n[3/5] Verifying DB contents...")
    import kuzu
    db_path = '/home/cuizhixing/cognee-env/lib/python3.10/site-packages/cognee/.cognee_system/databases/cognee_graph_kuzu'
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    # Check nodes
    result_nodes = conn.execute('MATCH (n:Node) RETURN n.type, n.name, COUNT(*) as cnt ORDER BY cnt DESC')
    print("  Node counts:")
    total_nodes = 0
    while result_nodes.has_next():
        row = result_nodes.get_next()
        print(f"    {row[0]}: {row[2]} (sample: {row[1] or '(unnamed)'})")
        total_nodes += row[2]
    print(f"  Total nodes: {total_nodes}")

    # Check for empty names
    result_empty = conn.execute('MATCH (n:Node) WHERE n.name = "" RETURN n.type, COUNT(*) as cnt')
    empty_count = 0
    while result_empty.has_next():
        row = result_empty.get_next()
        if row[1] > 0:
            print(f"  ⚠️  Empty names in {row[0]}: {row[1]}")
            empty_count += row[1]
    if empty_count == 0:
        print("  ✅ No empty node names")

    # Check edges
    result_edges = conn.execute('MATCH (a:Node)-[r]->(b:Node) RETURN COUNT(*) as cnt')
    edge_count = result_edges.get_next()[0] if result_edges.has_next() else 0
    print(f"  Total edges: {edge_count}")

    # Show some edges
    result_edge_sample = conn.execute(
        'MATCH (a:Node)-[r]->(b:Node) RETURN a.name, r.relationship_name, b.name LIMIT 20'
    )
    print("  Sample edges:")
    while result_edge_sample.has_next():
        row = result_edge_sample.get_next()
        src = row[0] or '(unnamed)'
        dst = row[2] or '(unnamed)'
        print(f"    {src[:40]} --{row[1]}--> {dst[:40]}")

    # 4. Check for test data pollution
    print("\n[4/5] Checking for test data pollution...")
    pollutants = ['Machine Translation', 'WMT-14', 'LoRA', 'A', 'B']
    found_pollutants = []
    for p in pollutants:
        res = conn.execute(f'MATCH (n:Node) WHERE n.name = "{p}" RETURN COUNT(*) as cnt')
        if res.has_next() and res.get_next()[0] > 0:
            found_pollutants.append(p)
    if found_pollutants:
        print(f"  ⚠️  Found test data pollutants: {found_pollutants}")
    else:
        print("  ✅ No test data pollutants found")

    # 5. Check for duplicates
    print("\n[5/5] Checking for duplicates...")
    result_dups = conn.execute(
        'MATCH (n:Node) RETURN n.name, n.type, COUNT(*) as cnt ORDER BY cnt DESC'
    )
    dups_found = False
    while result_dups.has_next():
        row = result_dups.get_next()
        if row[2] > 1 and row[0]:
            print(f"  ⚠️  Duplicate: '{row[0]}' [{row[1]}] x{row[2]}")
            dups_found = True
    if not dups_found:
        print("  ✅ No duplicate nodes")

    print("\n" + "=" * 70)
    print("PIPELINE TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
