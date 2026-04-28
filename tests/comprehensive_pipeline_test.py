"""Comprehensive pipeline test - outputs every stage for human review."""
import sys, os, asyncio, json, shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, '/home/cuizhixing/cognee-env/lib/python3.10/site-packages')

# Configure Cognee embeddings before anything else
import cognee
cognee.config.set_embedding_provider("fastembed")
cognee.config.set_embedding_model("jinaai/jina-embeddings-v3")
cognee.config.set_embedding_dimensions(1024)

# Clear caches
from cognee.infrastructure.databases.vector.create_vector_engine import _create_vector_engine
from cognee.infrastructure.databases.vector.embeddings.get_embedding_engine import create_embedding_engine
_create_vector_engine.cache_clear()
create_embedding_engine.cache_clear()

TEST_PAPER = "/home/cuizhixing/.openclaw/workspace-scientist/科研内容/论文仓库/05_LLM工具与智能体记忆/2601.03559.pdf"
OUTPUT_DIR = "/home/cuizhixing/research_graph/tests/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def main():
    print("=" * 70)
    print("COMPREHENSIVE PIPELINE TEST")
    print("=" * 70)

    # 0. Clean DB
    print("\n[0/8] Cleaning DB...")
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    db_path = '/home/cuizhixing/cognee-env/lib/python3.10/site-packages/cognee/.cognee_system/databases/cognee_graph_kuzu'
    lancedb_path = '/home/cuizhixing/cognee-env/lib/python3.10/site-packages/cognee/.cognee_system/databases/cognee.lancedb'
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(lancedb_path):
        shutil.rmtree(lancedb_path)
    print("  ✅ DB cleaned")

    # 1. GROBID Parse → Markdown
    print("\n[1/8] GROBID Parsing PDF → Structured Text...")
    from src.parsing.grobid_client import GrobidClient
    client = GrobidClient()
    paper = client.parse_pdf(TEST_PAPER)

    # Build markdown
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
    markdown_text = "\n".join(lines)

    md_path = os.path.join(OUTPUT_DIR, "01_pdf_to_markdown.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    print(f"  ✅ Saved: {md_path} ({len(markdown_text)} chars, {len(paper.sections)} sections)")

    # 2. Paper metadata
    print("\n[2/8] Paper Metadata...")
    paper_title = paper.title
    authors = ", ".join(paper.authors) if paper.authors else "Unknown"
    abstract = paper.abstract or ""
    print(f"  Title: {paper_title[:60]}...")
    print(f"  Authors: {authors[:60]}...")

    # 3. Stage 1a: Top-level Method + Problem extraction (Intro + Method)
    print("\n[3/8] Stage 1a: Top-level Method + Problem Extraction...")
    from src.extraction.pipeline import AcademicExtractor
    from src.extraction.prompts import get_extraction_prompt_1a, get_extraction_prompt_1b, get_insight_prompt_v2
    extractor = AcademicExtractor()
    intro_text = extractor._merge_sections(paper.sections,
        ["Abstract", "Introduction", "Related Work", "Background"])
    method_text = extractor._merge_sections(paper.sections,
        ["Method", "Methods", "Approach", "Model", "Architecture", "Proposed Method"])
    exp_text = extractor._merge_sections(paper.sections,
        ["Experiments", "Experimental Setup", "Results", "Evaluation", "Empirical Study"])

    stage1a_input = f"{intro_text[:2500]}\n\n{method_text[:5000]}\n\n{exp_text[:2000]}"
    stage1a_raw = await extractor.llm.complete(
        get_extraction_prompt_1a(stage1a_input, paper_title, authors, abstract)
    )
    stage1a = extractor._safe_parse_json(stage1a_raw)

    stage1a_path = os.path.join(OUTPUT_DIR, "03_stage1a_raw_extraction.json")
    with open(stage1a_path, "w", encoding="utf-8") as f:
        json.dump(stage1a, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Saved: {stage1a_path}")
    print(f"  Top-level methods: {len(stage1a.get('entities', {}).get('methods', []))}")
    print(f"  Problems: {len(stage1a.get('entities', {}).get('problems', []))}")
    print(f"  Resources: {len(stage1a.get('entities', {}).get('resources', []))}")
    print(f"  Relations: {len(stage1a.get('relations', []))}")

    # 4. Stage 1b: Sub-method + Component extraction (Method deep dive)
    print("\n[4/8] Stage 1b: Sub-method + Component Extraction...")
    top_level_name = stage1a.get('entities', {}).get('methods', [{}])[0].get('name', 'Unknown')
    stage1b_raw = await extractor.llm.complete(
        get_extraction_prompt_1b(method_text[:8000], paper_title, authors, abstract, top_level_name)
    )
    stage1b = extractor._safe_parse_json(stage1b_raw)

    stage1b_path = os.path.join(OUTPUT_DIR, "04_stage1b_raw_extraction.json")
    with open(stage1b_path, "w", encoding="utf-8") as f:
        json.dump(stage1b, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Saved: {stage1b_path}")
    print(f"  Sub-methods/components: {len(stage1b.get('sub_methods', []))}")
    print(f"  Relations: {len(stage1b.get('relations', []))}")

    # Merge for display
    all_methods = list(stage1a.get('entities', {}).get('methods', [])) + list(stage1b.get('sub_methods', []))
    all_problems = list(stage1a.get('entities', {}).get('problems', []))
    print(f"  Total methods after merge: {len(all_methods)}")

    # 5. Stage 2: Insight extraction (from Experiments, with entity association)
    print("\n[5/8] Stage 2: Insight Extraction...")
    method_names = [m['name'] for m in all_methods]
    problem_names = [p['name'] for p in all_problems]
    stage2_raw = await extractor.llm.complete(
        get_insight_prompt_v2(exp_text[:6000], paper_title, authors, abstract, method_names, problem_names)
    )
    stage2 = extractor._safe_parse_json(stage2_raw)

    stage2_path = os.path.join(OUTPUT_DIR, "05_stage2_raw_insights.json")
    with open(stage2_path, "w", encoding="utf-8") as f:
        json.dump(stage2, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Saved: {stage2_path}")
    print(f"  Raw insights: {len(stage2.get('insights', []))}")

    # 6. Entity Resolution (Normalization)
    print("\n[6/8] Entity Resolution (Normalization)...")
    from src.resolution.resolver import EntityResolver
    resolver = EntityResolver("data/aliases.json")
    merged_entities = {
        "methods": all_methods,
        "problems": all_problems,
        "resources": list(stage1a.get('entities', {}).get('resources', [])),
    }
    normalized = await resolver.resolve_batch(merged_entities)

    # Show what got changed
    changes = []
    for category in ["methods", "problems", "resources"]:
        raw_names = [e["name"] for e in merged_entities.get(category, [])]
        norm_names = [e["name"] for e in normalized.get(category, [])]
        for r, n in zip(raw_names, norm_names):
            if r != n:
                changes.append(f"    {category}: '{r}' → '{n}'")

    norm_path = os.path.join(OUTPUT_DIR, "06_normalized_entities.json")
    with open(norm_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Saved: {norm_path}")
    print(f"  Normalized methods: {len(normalized.get('methods', []))}")
    print(f"  Normalized problems: {len(normalized.get('problems', []))}")
    print(f"  Normalized resources: {len(normalized.get('resources', []))}")
    if changes:
        print(f"  ⚠️  Resolution changed {len(changes)} names:")
        for c in changes[:10]:
            print(c)
        if len(changes) > 10:
            print(f"    ... and {len(changes) - 10} more")
    else:
        print("  ✅ No names were changed by resolution")

    # 7. Full Extract → Store in DB
    print("\n[7/8] Full Extract + Store to Cognee DB...")
    result = await extractor.extract(paper, "comprehensive_test")
    print(f"  Paper title: {result['paper_title'][:50]}...")
    print(f"  Methods: {result['methods']}")
    print(f"  Problems: {result['problems']}")
    print(f"  Resources: {result['resources']}")
    print(f"  Insights: {result['insights']}")
    print(f"  Relations: {result['relations']}")

    # 8. Dump DB Contents
    print("\n[8/9] Dumping Database Contents...")
    import kuzu
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    db_report = []
    db_report.append("=" * 70)
    db_report.append("COGNEE GRAPH DATABASE CONTENT REPORT")
    db_report.append("=" * 70)

    # All nodes
    res = conn.execute('MATCH (n:Node) RETURN n.id, n.type, n.name ORDER BY n.type, n.name')
    nodes = []
    while res.has_next():
        row = res.get_next()
        nodes.append({"id": str(row[0]), "type": row[1], "name": row[2] or "(unnamed)"})

    type_counts = {}
    for n in nodes:
        t = n["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    db_report.append(f"\nTotal Nodes: {len(nodes)}")
    db_report.append("Node Type Breakdown:")
    for t, c in sorted(type_counts.items()):
        db_report.append(f"  {t}: {c}")

    db_report.append(f"\n{'='*70}")
    db_report.append("ALL NODES")
    db_report.append(f"{'='*70}")
    for n in nodes:
        db_report.append(f"  [{n['type']}] {n['name']}")

    # All edges
    res2 = conn.execute('MATCH (a:Node)-[r]->(b:Node) RETURN a.name, r.relationship_name, b.name, a.type, b.type')
    edges = []
    while res2.has_next():
        row = res2.get_next()
        edges.append({
            "src_name": row[0] or "(unnamed)",
            "rel": row[1],
            "dst_name": row[2] or "(unnamed)",
            "src_type": row[3],
            "dst_type": row[4],
        })

    db_report.append(f"\n{'='*70}")
    db_report.append(f"ALL EDGES (Total: {len(edges)})")
    db_report.append(f"{'='*70}")
    for e in edges:
        db_report.append(f"  [{e['src_type']}] {e['src_name'][:50]} --{e['rel']}--> [{e['dst_type']}] {e['dst_name'][:50]}")

    # Check empty names
    res3 = conn.execute('MATCH (n:Node) WHERE n.name = "" RETURN n.type, COUNT(*) as cnt')
    empty_found = False
    while res3.has_next():
        row = res3.get_next()
        if row[1] > 0:
            db_report.append(f"\n  ⚠️  Empty names in {row[0]}: {row[1]}")
            empty_found = True
    if not empty_found:
        db_report.append("\n  ✅ No empty node names")

    # Check duplicates
    res4 = conn.execute('MATCH (n:Node) RETURN n.name, n.type, COUNT(*) as cnt ORDER BY cnt DESC')
    dups_found = False
    while res4.has_next():
        row = res4.get_next()
        if row[2] > 1 and row[0]:
            db_report.append(f"  ⚠️  Duplicate: '{row[0]}' [{row[1]}] x{row[2]}")
            dups_found = True
    if not dups_found:
        db_report.append("  ✅ No duplicate nodes")

    db_report_path = os.path.join(OUTPUT_DIR, "07_database_contents.txt")
    with open(db_report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(db_report))
    print(f"  ✅ Saved: {db_report_path}")

    # 9. Test Taxonomy Builder (Recursive)
    print("\n[9/9] Testing Recursive Taxonomy Builder...")
    from src.taxonomy.builder import RecursiveTaxonomyBuilder
    from src.models.academic_nodes import Method, Problem

    # Get methods from DB
    method_nodes_db = [n for n in nodes if n["type"] == "Method"]
    problem_nodes_db = [n for n in nodes if n["type"] == "Problem"]

    print(f"  Methods in DB: {len(method_nodes_db)}")
    print(f"  Problems in DB: {len(problem_nodes_db)}")

    # Build recursive method tree with LLM
    tb = RecursiveTaxonomyBuilder(llm_client=extractor.llm)
    methods_for_tree = [Method(name=n["name"], description="") for n in method_nodes_db]
    method_root = await tb.build_method_tree(methods_for_tree)
    if method_root:
        print(f"  Method tree root: {method_root.name} (level {method_root.level})")
        _print_tree(method_root, indent=4)

    # Build recursive problem tree with LLM
    problems_for_tree = [Problem(name=n["name"], description="") for n in problem_nodes_db]
    problem_root = await tb.build_problem_tree(problems_for_tree)
    if problem_root:
        print(f"  Problem tree root: {problem_root.name} (level {problem_root.level})")
        _print_tree(problem_root, indent=4)

    taxonomy_path = os.path.join(OUTPUT_DIR, "08_taxonomy_results.txt")
    with open(taxonomy_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("RECURSIVE TAXONOMY BUILDER RESULTS\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Methods in DB: {len(method_nodes_db)}\n")
        if method_root:
            f.write(f"Method tree root: {method_root.name} (level {method_root.level})\n")
            _write_tree(f, method_root)
        f.write(f"\nProblems in DB: {len(problem_nodes_db)}\n")
        if problem_root:
            f.write(f"Problem tree root: {problem_root.name} (level {problem_root.level})\n")
            _write_tree(f, problem_root)
    print(f"  ✅ Saved: {taxonomy_path}")

    # Summary
    print("\n" + "=" * 70)
    print("TEST COMPLETE - All 9 stages finished, outputs saved to tests/output/")
    print("=" * 70)
    for fname in sorted(os.listdir(OUTPUT_DIR)):
        fpath = os.path.join(OUTPUT_DIR, fname)
        size = os.path.getsize(fpath)
        print(f"  {fname:40s} {size:>10,} bytes")


def _print_tree(node, indent=0):
    prefix = " " * indent + "- "
    print(f"{prefix}{node.name} [{node.node_type}]")
    for child in (node.children or []):
        _print_tree(child, indent + 2)


def _write_tree(f, node, indent=0):
    prefix = "  " * indent + "- "
    f.write(f"{prefix}{node.name} [{node.node_type}]\n")
    for child in (node.children or []):
        _write_tree(f, child, indent + 1)


if __name__ == "__main__":
    asyncio.run(main())
