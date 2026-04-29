import json
import sys
sys.path.insert(0, '/home/cuizhixing/cognee-env/lib/python3.10/site-packages')
sys.path.insert(0, '/home/cuizhixing/research_graph')

import os
import asyncio
from typing import Optional

# Initialize Cognee BEFORE any other imports (creates relational DB + default user)
from src.config.cognee_init import ensure_cognee_initialized_async

from cognee.tasks.storage import add_data_points

from src.models.academic_nodes import (
    Paper, Method, Problem, Insight, Resource,
    PaperRelations, MethodRelations, ProblemRelations
)
from src.extraction.prompts import (
    get_extraction_prompt_1a,
    get_extraction_prompt_1b,
    get_insight_prompt_v2,
)
from src.resolution.resolver import EntityResolver
from src.parsing.grobid_client import PaperStruct


class SimpleLLMClient:
    """Minimal async LLM client supporting OpenAI or Anthropic (Kimi Code) APIs."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        # Auto-detect Kimi Code API (Anthropic-compatible)
        anthropic_key = api_key or os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY")
        anthropic_base = base_url or os.getenv("ANTHROPIC_BASE_URL") or os.getenv("ANTHROPIC_API_BASE")

        if anthropic_key and anthropic_base:
            import anthropic
            self._provider = "anthropic"
            self.client = anthropic.AsyncAnthropic(api_key=anthropic_key, base_url=anthropic_base)
            self.model = model or os.getenv("ANTHROPIC_MODEL", "kimi-for-coding")
            return

        # Fallback to OpenAI-compatible API (e.g. Moonshot)
        openai_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("KIMI_API_KEY") or os.getenv("OPENAI_API_KEY")
        openai_base = base_url or os.getenv("LLM_BASE_URL", "https://api.moonshot.cn/v1")
        if not openai_key:
            raise ValueError(
                "No LLM API key found. Set one of: ANTHROPIC_AUTH_TOKEN, ANTHROPIC_API_KEY, "
                "LLM_API_KEY, KIMI_API_KEY, or OPENAI_API_KEY."
            )
        from openai import AsyncOpenAI
        self._provider = "openai"
        self.client = AsyncOpenAI(api_key=openai_key, base_url=openai_base)
        self.model = model or os.getenv("LLM_MODEL", "kimi-latest")

    async def complete(self, prompt: str, temperature: float = 0.3, max_tokens: int = 4096) -> str:
        system_msg = "You are a precise academic information extraction assistant. Always return valid JSON."
        if self._provider == "anthropic":
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_msg,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text if response.content else ""
        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""


class AcademicExtractor:
    def __init__(self, llm_client: Optional[SimpleLLMClient] = None, resolver: Optional[EntityResolver] = None):
        self.llm = llm_client or SimpleLLMClient()
        self.resolver = resolver or EntityResolver("data/aliases.json")

    async def extract(self, paper_struct: PaperStruct, paper_id: str) -> dict:
        # Ensure Cognee is initialized (creates relational DB + default user)
        await ensure_cognee_initialized_async()

        # Paper metadata for prompt injection
        paper_title = paper_struct.title
        authors = ", ".join(paper_struct.authors) if paper_struct.authors else "Unknown"
        abstract = paper_struct.abstract or ""

        # 1. Merge sections by semantic role
        intro_text = self._merge_sections(paper_struct.sections,
            ["Abstract", "Introduction", "Related Work", "Background"])
        method_text = self._merge_sections(paper_struct.sections,
            ["Method", "Methods", "Approach", "Model", "Architecture", "Proposed Method"])
        exp_text = self._merge_sections(paper_struct.sections,
            ["Experiments", "Experimental Setup", "Results", "Evaluation", "Empirical Study"])

        # 2. Stage 1a: Extract top-level methods, problems, resources from Intro+Method+Experiments(partial)
        # Include partial Experiments text so datasets/benchmarks are captured
        stage1a_input = f"{intro_text[:2500]}\n\n{method_text[:5000]}\n\n{exp_text[:2000]}"
        stage1a_raw = await self.llm.complete(
            get_extraction_prompt_1a(stage1a_input, paper_title, authors, abstract)
        )
        stage1a = self._safe_parse_json(stage1a_raw)
        print(f"[Extractor] Stage 1a raw: {len(stage1a.get('entities', {}).get('methods', []))} methods, "
              f"{len(stage1a.get('entities', {}).get('problems', []))} problems, "
              f"{len(stage1a.get('entities', {}).get('resources', []))} resources")

        # 3. Stage 1b: Extract sub-methods and components from Method (deep dive)
        top_level_methods = stage1a.get("entities", {}).get("methods", [])
        top_level_name = top_level_methods[0]["name"] if top_level_methods else "Unknown"

        stage1b_raw = await self.llm.complete(
            get_extraction_prompt_1b(method_text[:8000], paper_title, authors, abstract, top_level_name)
        )
        stage1b = self._safe_parse_json(stage1b_raw)
        print(f"[Extractor] Stage 1b raw: {len(stage1b.get('sub_methods', []))} sub-methods/components")

        # 4. Merge Stage 1a and 1b results
        all_methods = list(top_level_methods) + list(stage1b.get("sub_methods", []))
        all_problems = list(stage1a.get("entities", {}).get("problems", []))
        all_resources = list(stage1a.get("entities", {}).get("resources", []))
        all_relations = list(stage1a.get("relations", [])) + list(stage1b.get("relations", []))

        # 5. Entity resolution (normalize names, dedup)
        merged_entities = {
            "methods": all_methods,
            "problems": all_problems,
            "resources": all_resources,
        }
        normalized = await self.resolver.resolve_batch(merged_entities)

        # 6. Stage 2: Insight extraction (from Experiments, with entity association)
        method_names = [m["name"] for m in normalized.get("methods", [])]
        problem_names = [p["name"] for p in normalized.get("problems", [])]
        stage2_raw = await self.llm.complete(
            get_insight_prompt_v2(exp_text[:6000], paper_title, authors, abstract, method_names, problem_names)
        )
        stage2 = self._safe_parse_json(stage2_raw)
        print(f"[Extractor] Stage 2 raw: {len(stage2.get('insights', []))} insights")

        # 7. Build DataPoint nodes
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
                description=r.get("description", ""),
            )

        insight_nodes = []
        for i in stage2.get("insights", []):
            insight_nodes.append(Insight(
                statement=i["statement"],
                insight_type=i.get("type", "empirical_finding"),
                confidence=i.get("confidence", "medium"),
                evidence_quote=i.get("evidence_quote", ""),
                from_paper=paper_node,
            ))

        # 8. Build PaperRelations (proposes/uses/addresses/evaluates_on/contains_insight)
        paper_rels = PaperRelations(paper=paper_node)
        paper_rels.addresses = list(problem_nodes.values())
        paper_rels.contains_insight = insight_nodes
        paper_rels.evaluates_on = list(resource_nodes.values())

        proposes_names = set()
        uses_names = set()
        for rel in all_relations:
            pred = rel.get("predicate")
            obj_type = rel.get("object_type")
            obj_name = rel.get("object_name")
            if pred == "proposes" and obj_type == "Method" and obj_name in method_nodes:
                proposes_names.add(obj_name)
            elif pred == "uses" and obj_type == "Method" and obj_name in method_nodes:
                uses_names.add(obj_name)

        paper_rels.proposes = [method_nodes[n] for n in proposes_names]
        paper_rels.uses = [method_nodes[n] for n in uses_names]

        # 9. Build MethodRelations (contains, uses_technique, improves_upon, etc.)
        async def _resolve_name(raw_name: str, entity_type: str) -> str:
            return await self.resolver.resolve(raw_name, entity_type)

        method_rel_map = {}
        for rel in all_relations:
            pred = rel.get("predicate")
            if pred in ("proposes", "uses", "addresses", "is_subtask_of"):
                continue  # Handled by PaperRelations or ProblemRelations

            sub = await _resolve_name(rel.get("subject_name", ""), "method")
            obj_raw = rel.get("object_name", "")
            obj_type = rel.get("object_type")

            if obj_type == "Method":
                obj = await _resolve_name(obj_raw, "method")
                target = method_nodes.get(obj)
            elif obj_type == "Problem":
                obj = await _resolve_name(obj_raw, "problem")
                target = problem_nodes.get(obj)
            else:
                continue

            if target is None or sub not in method_nodes:
                continue

            if sub not in method_rel_map:
                method_rel_map[sub] = {}
            if pred not in method_rel_map[sub]:
                method_rel_map[sub][pred] = []
            method_rel_map[sub][pred].append(target)

        method_rels = []
        for method_name, rels in method_rel_map.items():
            mr = MethodRelations(method=method_nodes[method_name])
            if "contains" in rels:
                mr.contains = rels["contains"]
            if "uses_technique" in rels:
                mr.uses_technique = rels["uses_technique"]
            if "improves_upon" in rels:
                mr.improves_upon = rels["improves_upon"]
            if "is_variant_of" in rels:
                mr.is_variant_of = rels["is_variant_of"]
            if "combines" in rels:
                mr.combines = rels["combines"]
            if "solves" in rels:
                mr.solves = rels["solves"]
            if "partially_solves" in rels:
                mr.partially_solves = rels["partially_solves"]
            method_rels.append(mr)

        # 10. Build ProblemRelations (is_subtask_of)
        problem_rel_map = {}
        for rel in all_relations:
            if rel.get("predicate") != "is_subtask_of":
                continue
            sub = await _resolve_name(rel.get("subject_name", ""), "problem")
            obj = await _resolve_name(rel.get("object_name", ""), "problem")
            obj_type = rel.get("object_type")
            if sub not in problem_nodes:
                continue
            if obj_type == "Problem" and obj in problem_nodes:
                target = problem_nodes[obj]
            else:
                continue
            if sub not in problem_rel_map:
                problem_rel_map[sub] = {}
            if "is_subtask_of" not in problem_rel_map[sub]:
                problem_rel_map[sub]["is_subtask_of"] = []
            problem_rel_map[sub]["is_subtask_of"].append(target)

        problem_rels = []
        for problem_name, rels in problem_rel_map.items():
            pr = ProblemRelations(problem=problem_nodes[problem_name])
            if "is_subtask_of" in rels:
                pr.is_subtask_of = rels["is_subtask_of"]
            problem_rels.append(pr)

        # 11. Write to Cognee
        all_nodes = [paper_node, paper_rels]
        all_nodes.extend(method_nodes.values())
        all_nodes.extend(problem_nodes.values())
        all_nodes.extend(resource_nodes.values())
        all_nodes.extend(insight_nodes)
        all_nodes.extend(method_rels)
        all_nodes.extend(problem_rels)

        await add_data_points(all_nodes)

        return {
            "paper_id": paper_id,
            "paper_title": paper_title,
            "methods": list(method_nodes.keys()),
            "problems": list(problem_nodes.keys()),
            "resources": list(resource_nodes.keys()),
            "insights": len(insight_nodes),
            "relations": len(all_relations),
        }

    def _merge_sections(self, sections, target_headings):
        texts = []
        for s in sections:
            heading = s["heading"].lower()
            if any(t.lower() in heading for t in target_headings):
                texts.append(s["text"])
        return "\n\n".join(texts)

    def _safe_parse_json(self, raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                start = text.index("{")
                end = text.rindex("}") + 1
                return json.loads(text[start:end])
            except (ValueError, json.JSONDecodeError):
                return {}
