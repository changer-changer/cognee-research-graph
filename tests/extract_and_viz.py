"""Extract data without DB write, then generate visualization and evaluation."""
import sys, os, json, asyncio

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, '/home/cuizhixing/cognee-env/lib/python3.10/site-packages')

from src.parsing.grobid_client import GrobidClient
from src.extraction.pipeline import AcademicExtractor, SimpleLLMClient
from src.resolution.resolver import EntityResolver
from src.models.academic_nodes import Paper, Method, Problem, Insight, Resource, PaperRelations, MethodRelations

TEST_PAPER = "/home/cuizhixing/.openclaw/workspace/科研内容/论文仓库/05_LLM工具与智能体记忆/2601.01982.pdf"


class NoOpExtractor(AcademicExtractor):
    """Override extract to skip add_data_points (DB write)."""

    async def extract(self, paper_struct, paper_id):
        # Reuse parent's logic but skip the DB write at the end
        intro_text = self._merge_sections(paper_struct.sections,
            ["Abstract", "Introduction", "Related Work", "Background"])
        method_text = self._merge_sections(paper_struct.sections,
            ["Method", "Methods", "Approach", "Model", "Architecture", "Proposed Method"])
        exp_text = self._merge_sections(paper_struct.sections,
            ["Experiments", "Experimental Setup", "Results", "Evaluation", "Empirical Study"])

        stage1_input = f"## Introduction & Method\n{intro_text[:4000]}\n\n## Method Details\n{method_text[:4000]}"
        stage1_raw = await self.llm.complete(self._get_extraction_prompt(stage1_input))
        stage1 = self._safe_parse_json(stage1_raw)

        normalized = await self.resolver.resolve_batch(stage1.get("entities", {}))

        stage2_input = f"## Experiments & Results\n{exp_text[:5000]}"
        stage2_raw = await self.llm.complete(self._get_insight_prompt(stage2_input))
        stage2 = self._safe_parse_json(stage2_raw)

        paper_node = Paper(
            title=paper_struct.title,
            authors=paper_struct.authors,
            year=paper_struct.year,
            venue=paper_struct.venue,
            doi=paper_struct.doi,
            abstract=paper_struct.abstract,
        )

        method_nodes = {}
        for m in normalized.get("methods", []):
            name = m["name"]
            method_nodes[name] = Method(
                name=name,
                description=m.get("description", ""),
                method_type=m.get("type", "unknown"),
            )

        problem_nodes = {}
        for p in normalized.get("problems", []):
            name = p["name"]
            problem_nodes[name] = Problem(
                name=name,
                description=p.get("description", ""),
                problem_level=p.get("level", "task"),
            )

        resource_nodes = {}
        for r in normalized.get("resources", []):
            name = r["name"]
            resource_nodes[name] = Resource(
                name=name,
                resource_type=r.get("type", "dataset"),
                description="",
            )

        insight_nodes = []
        for i in stage2.get("insights", []):
            insight_nodes.append(Insight(
                statement=i["statement"],
                insight_type=i.get("type", "empirical_finding"),
                confidence=i.get("confidence", "medium"),
                evidence_quote=i.get("evidence_quote", ""),
            ))

        paper_rels = PaperRelations(paper=paper_node)
        paper_rels.addresses = list(problem_nodes.values())
        paper_rels.contains_insight = insight_nodes
        paper_rels.evaluates_on = list(resource_nodes.values())

        proposes_names = set()
        uses_names = set()
        for rel in stage1.get("relations", []):
            if rel.get("predicate") == "proposes" and rel.get("object_type") == "Method":
                proposes_names.add(rel["object_name"])
            elif rel.get("predicate") == "uses" and rel.get("object_type") == "Method":
                uses_names.add(rel["object_name"])

        paper_rels.proposes = [method_nodes[n] for n in proposes_names if n in method_nodes]
        paper_rels.uses = [method_nodes[n] for n in uses_names if n in method_nodes]

        method_rels = []
        for rel in stage1.get("relations", []):
            if rel.get("subject_type") == "Method" and rel.get("object_type") == "Method":
                sub = rel["subject_name"]
                obj = rel["object_name"]
                pred = rel["predicate"]
                if sub in method_nodes and obj in method_nodes:
                    mr = MethodRelations(method=method_nodes[sub])
                    if pred == "improves_upon":
                        mr.improves_upon = [method_nodes[obj]]
                    elif pred == "is_variant_of":
                        mr.is_variant_of = [method_nodes[obj]]
                    elif pred == "combines":
                        mr.combines = [method_nodes[obj]]
                    method_rels.append(mr)

            if rel.get("subject_type") == "Method" and rel.get("object_type") == "Problem":
                sub = rel["subject_name"]
                obj = rel["object_name"]
                pred = rel["predicate"]
                if sub in method_nodes and obj in problem_nodes:
                    mr = MethodRelations(method=method_nodes[sub])
                    if pred == "solves":
                        mr.solves = [problem_nodes[obj]]
                    elif pred == "partially_solves":
                        mr.partially_solves = [problem_nodes[obj]]
                    method_rels.append(mr)

        return {
            "paper_id": paper_id,
            "paper": paper_node,
            "methods": list(method_nodes.values()),
            "problems": list(problem_nodes.values()),
            "resources": list(resource_nodes.values()),
            "insights": insight_nodes,
            "relations": stage1.get("relations", []),
            "paper_rels": paper_rels,
            "method_rels": method_rels,
            "raw_stage1": stage1,
            "raw_stage2": stage2,
        }

    def _get_extraction_prompt(self, text):
        from src.extraction.prompts import get_extraction_prompt
        return get_extraction_prompt(text)

    def _get_insight_prompt(self, text):
        from src.extraction.prompts import get_insight_prompt
        return get_insight_prompt(text)


async def main():
    print("=" * 60)
    print("Extracting graph data (no DB write)...")
    print("=" * 60)

    client = GrobidClient()
    paper = client.parse_pdf(TEST_PAPER)
    extractor = NoOpExtractor(resolver=EntityResolver("data/aliases.json"))
    result = await extractor.extract(paper, "eval_001")

    # Print raw extraction results
    print("\n--- Raw Stage 1 (Entities + Relations) ---")
    print(json.dumps(result["raw_stage1"], indent=2, ensure_ascii=False))

    print("\n--- Raw Stage 2 (Insights) ---")
    print(json.dumps(result["raw_stage2"], indent=2, ensure_ascii=False))

    print("\n--- Structured Nodes ---")
    print(f"Paper: {result['paper'].title}")
    print(f"Methods: {[m.name for m in result['methods']]}")
    print(f"Problems: {[p.name for p in result['problems']]}")
    print(f"Resources: {[r.name for r in result['resources']]}")
    print(f"Insights: {len(result['insights'])}")
    for i in result["insights"]:
        print(f"  - [{i.confidence}] {i.statement[:100]}")
    print(f"Relations: {len(result['relations'])}")
    for r in result["relations"]:
        print(f"  - {r.get('subject_name')} --{r.get('predicate')}--> {r.get('object_name')}")

    # Build graph data for visualization
    nodes = []
    edges = []

    # Paper node
    nodes.append({"id": "paper", "label": paper.title[:50], "type": "Paper"})

    # Method nodes
    for i, m in enumerate(result["methods"]):
        nid = f"method_{i}"
        nodes.append({"id": nid, "label": m.name, "type": "Method", "desc": m.description[:80]})
        edges.append({"from": "paper", "to": nid, "label": "proposes/uses"})

    # Problem nodes
    for i, p in enumerate(result["problems"]):
        nid = f"problem_{i}"
        nodes.append({"id": nid, "label": p.name, "type": "Problem", "desc": p.description[:80]})
        edges.append({"from": "paper", "to": nid, "label": "addresses"})

    # Resource nodes
    for i, r in enumerate(result["resources"]):
        nid = f"resource_{i}"
        nodes.append({"id": nid, "label": r.name, "type": "Resource"})
        edges.append({"from": "paper", "to": nid, "label": "evaluates_on"})

    # Insight nodes
    for i, ins in enumerate(result["insights"]):
        nid = f"insight_{i}"
        nodes.append({"id": nid, "label": ins.statement[:60], "type": "Insight", "confidence": ins.confidence})
        edges.append({"from": "paper", "to": nid, "label": "contains_insight"})

    # Method-Method / Method-Problem relations
    for rel in result["relations"]:
        if rel.get("subject_type") == "Method" and rel.get("object_type") == "Method":
            # Find node ids
            sub_id = None
            obj_id = None
            for j, m in enumerate(result["methods"]):
                if m.name == rel["subject_name"]:
                    sub_id = f"method_{j}"
                if m.name == rel["object_name"]:
                    obj_id = f"method_{j}"
            if sub_id and obj_id:
                edges.append({"from": sub_id, "to": obj_id, "label": rel["predicate"]})
        elif rel.get("subject_type") == "Method" and rel.get("object_type") == "Problem":
            sub_id = None
            obj_id = None
            for j, m in enumerate(result["methods"]):
                if m.name == rel["subject_name"]:
                    sub_id = f"method_{j}"
            for j, p in enumerate(result["problems"]):
                if p.name == rel["object_name"]:
                    obj_id = f"problem_{j}"
            if sub_id and obj_id:
                edges.append({"from": sub_id, "to": obj_id, "label": rel["predicate"]})

    # Save graph data
    graph_data = {"nodes": nodes, "edges": edges}
    with open("/home/cuizhixing/research_graph/viz/graph_data.json", "w") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)

    print(f"\nGraph data saved: {len(nodes)} nodes, {len(edges)} edges")
    return graph_data, result


if __name__ == "__main__":
    asyncio.run(main())
