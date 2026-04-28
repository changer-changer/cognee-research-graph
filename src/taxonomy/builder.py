import sys
sys.path.insert(0, '/home/cuizhixing/cognee-env/lib/python3.10/site-packages')

from typing import List, Optional, Dict, Any
import numpy as np
from sklearn.cluster import AgglomerativeClustering

from cognee.infrastructure.engine import DataPoint
from cognee.tasks.storage import add_data_points

from src.models.academic_nodes import Method, Problem


class TaxonomyNode(DataPoint):
    """Taxonomy tree node - can be leaf (original method) or category (LLM-summarized parent)."""
    name: str
    description: str = ""
    level: int = 0  # 0 = leaf, higher = closer to root
    node_type: str = "method_category"  # "method_category" | "problem_category" | "leaf"
    # Relationship to children (lower level nodes)
    children: Optional[List["TaxonomyNode"]] = None
    # For leaf nodes: reference to original method/problem
    source_methods: Optional[List[Method]] = None
    source_problems: Optional[List[Problem]] = None
    metadata: Dict[str, Any] = {"index_fields": ["name", "description"]}


TAXONOMY_SUMMARIZE_PROMPT = """You are building a research taxonomy tree. Given a group of related methods/techniques, create a higher-level category that unifies them.

## INPUT METHODS

{methods_text}

## TASK

Create a parent category that naturally groups these methods. The category should be:
- Specific enough to distinguish from unrelated areas
- General enough to cover all listed methods
- Named using standard academic terminology

## OUTPUT FORMAT

Return STRICT JSON:

{{
  "category_name": "concise 2-6 word name (e.g., 'Diffusion-based CoT Mechanisms', 'Step-level Optimization Techniques')",
  "category_description": "One sentence explaining what unifies these methods and their shared goal/principle",
  "shared_principle": "The core technical principle common to all (1-3 words, e.g., 'iterative denoising', 'reward ranking')"
}}
"""


class RecursiveTaxonomyBuilder:
    """Builds a taxonomy tree bottom-up: leaf methods → LLM-summarized parents → root."""

    def __init__(self, llm_client=None, embed_fn=None):
        self.llm = llm_client
        # Use fastembed if no embed_fn provided
        self._embed_fn = embed_fn
        self._embedding_engine = None

    async def _embed(self, text: str) -> List[float]:
        if self._embed_fn:
            return await self._embed_fn(text)
        if self._embedding_engine is None:
            from cognee.infrastructure.databases.vector.embeddings.get_embedding_engine import create_embedding_engine
            self._embedding_engine = create_embedding_engine()
        return await self._embedding_engine.embed_text(text)

    async def build_method_tree(self, methods: List[Method]) -> Optional[TaxonomyNode]:
        """Build recursive taxonomy tree from leaf methods. Returns the root node."""
        if not methods:
            return None
        if len(methods) == 1:
            return TaxonomyNode(
                name=methods[0].name,
                description=methods[0].description,
                level=0,
                node_type="leaf",
                source_methods=[methods[0]],
            )

        # Create leaf nodes
        leaves = []
        for m in methods:
            leaves.append(TaxonomyNode(
                name=m.name,
                description=m.description,
                level=0,
                node_type="leaf",
                source_methods=[m],
            ))

        # Build tree bottom-up
        root = await self._build_level(leaves)

        # Persist all nodes in the tree
        all_nodes = self._collect_nodes(root)
        if all_nodes:
            await add_data_points(all_nodes)

        return root

    async def build_problem_tree(self, problems: List[Problem]) -> Optional[TaxonomyNode]:
        """Build recursive taxonomy tree from leaf problems. Returns the root node."""
        if not problems:
            return None
        if len(problems) == 1:
            return TaxonomyNode(
                name=problems[0].name,
                description=problems[0].description,
                level=0,
                node_type="leaf",
                source_problems=[problems[0]],
            )

        leaves = []
        for p in problems:
            leaves.append(TaxonomyNode(
                name=p.name,
                description=p.description,
                level=0,
                node_type="leaf",
                source_problems=[p],
            ))

        root = await self._build_level(leaves, node_type="problem_category")

        all_nodes = self._collect_nodes(root)
        if all_nodes:
            await add_data_points(all_nodes)

        return root

    async def _build_level(self, nodes: List[TaxonomyNode], node_type: str = "method_category") -> TaxonomyNode:
        """Recursively build one level up. If only 1 node, return it. Otherwise group, summarize, recurse."""
        if len(nodes) <= 1:
            return nodes[0]

        # Group nodes into clusters of 3-5
        groups = await self._group_nodes(nodes)

        # Summarize each group into a parent category
        parents = []
        for group in groups:
            if len(group) == 1:
                parents.append(group[0])
            else:
                parent = await self._summarize_group(group, node_type)
                parents.append(parent)

        # If grouping didn't reduce the count, force merge the smallest groups
        if len(parents) == len(nodes) and len(nodes) > 1:
            # Pair up nodes
            new_groups = []
            for i in range(0, len(nodes), 2):
                if i + 1 < len(nodes):
                    new_groups.append([nodes[i], nodes[i + 1]])
                else:
                    new_groups.append([nodes[i]])
            parents = []
            for group in new_groups:
                if len(group) == 1:
                    parents.append(group[0])
                else:
                    parents.append(await self._summarize_group(group, node_type))

        # Recurse: build next level from parents
        for p in parents:
            p.level += 1  # Increment level as we go up

        return await self._build_level(parents, node_type)

    async def _group_nodes(self, nodes: List[TaxonomyNode], max_size: int = 5) -> List[List[TaxonomyNode]]:
        """Group nodes by embedding similarity. Returns list of groups."""
        if len(nodes) <= max_size:
            return [nodes]

        vectors = []
        for n in nodes:
            vec = await self._embed(f"{n.name}: {n.description}")
            vectors.append(vec)
        X = np.array(vectors)

        # Normalize for cosine distance
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms[norms == 0] = 1
        X_norm = X / norms

        # Determine number of clusters: aim for groups of 3-5
        n_clusters = max(2, len(nodes) // max_size + (1 if len(nodes) % max_size else 0))

        clustering = AgglomerativeClustering(
            n_clusters=n_clusters,
            metric="cosine",
            linkage="average",
        )
        labels = clustering.fit_predict(X_norm)

        groups: Dict[int, List[TaxonomyNode]] = {}
        for idx, label in enumerate(labels):
            groups.setdefault(label, []).append(nodes[idx])

        # If any group is too large, split it recursively
        result = []
        for group in groups.values():
            if len(group) > max_size:
                sub_groups = await self._group_nodes(group, max_size)
                result.extend(sub_groups)
            else:
                result.append(group)

        return result

    async def _summarize_group(self, nodes: List[TaxonomyNode], node_type: str) -> TaxonomyNode:
        """Use LLM to summarize a group of nodes into a parent category."""
        methods_text = "\n".join(
            f"{i+1}. {n.name}: {n.description or 'No description'}"
            for i, n in enumerate(nodes)
        )

        if self.llm is None:
            # Fallback: use common prefix heuristic
            names = [n.name for n in nodes]
            common_words = set(names[0].lower().split())
            for name in names[1:]:
                common_words &= set(name.lower().split())
            if common_words:
                category_name = " ".join(sorted(common_words)).title() + " Methods"
            else:
                category_name = f"Category of {len(nodes)} Methods"
            return TaxonomyNode(
                name=category_name,
                description=f"Group containing: {', '.join(names)}",
                level=0,
                node_type=node_type,
                children=nodes,
            )

        prompt = TAXONOMY_SUMMARIZE_PROMPT.replace("{methods_text}", methods_text)
        raw = await self.llm.complete(prompt, temperature=0.3, max_tokens=512)
        parsed = self._safe_parse_json(raw)

        category_name = parsed.get("category_name", f"Category of {len(nodes)} Methods")
        category_desc = parsed.get("category_description", f"Group containing {len(nodes)} methods")

        return TaxonomyNode(
            name=category_name,
            description=category_desc,
            level=0,
            node_type=node_type,
            children=nodes,
        )

    def _collect_nodes(self, root: Optional[TaxonomyNode]) -> List[TaxonomyNode]:
        """Collect all nodes in the tree for persistence."""
        if root is None:
            return []
        result = [root]
        for child in (root.children or []):
            result.extend(self._collect_nodes(child))
        return result

    def _safe_parse_json(self, raw: str) -> dict:
        import json
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


# Backward-compatible wrapper
class TaxonomyBuilder(RecursiveTaxonomyBuilder):
    """Legacy wrapper - delegates to RecursiveTaxonomyBuilder."""
    pass


async def build_problem_tree_legacy(problems: List[Problem]) -> List[Problem]:
    """Legacy function - kept for compatibility."""
    if len(problems) < 2:
        return problems

    for p in problems:
        for candidate_parent in problems:
            if p.name != candidate_parent.name:
                if p.name.lower() in candidate_parent.description.lower():
                    p.parent = candidate_parent

    await add_data_points(problems)
    return problems
