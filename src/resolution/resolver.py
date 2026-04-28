import json
import os
from typing import Dict, List


class EntityResolver:
    def __init__(self, aliases_path: str = "data/aliases.json"):
        self.aliases = self._load_aliases(aliases_path)
        self.learned_path = "data/learned_aliases.json"
        self.learned = self._load_aliases(self.learned_path)
        self.entity_vectors: Dict[str, List[float]] = {}
        self.review_queue: List[Dict] = []

    def _load_aliases(self, path: str) -> Dict[str, str]:
        if not os.path.exists(path):
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _save_learned(self):
        os.makedirs(os.path.dirname(self.learned_path) or ".", exist_ok=True)
        with open(self.learned_path, "w", encoding="utf-8") as f:
            json.dump(self.learned, f, indent=2, ensure_ascii=False)

    async def resolve_batch(self, entities: Dict) -> Dict:
        result = {"methods": [], "problems": [], "resources": []}
        for m in entities.get("methods", []):
            m["name"] = await self.resolve(m["name"], "method")
            result["methods"].append(m)
        for p in entities.get("problems", []):
            p["name"] = await self.resolve(p["name"], "problem")
            result["problems"].append(p)
        for r in entities.get("resources", []):
            r["name"] = await self.resolve(r["name"], "resource")
            result["resources"].append(r)

        # Intra-batch deduplication: merge acronym/fullname pairs and near-duplicates
        result["methods"] = self._dedup_batch(result["methods"])
        result["problems"] = self._dedup_batch(result["problems"])
        return result

    def _dedup_batch(self, items: List[Dict]) -> List[Dict]:
        """Merge items within a batch that are clearly the same entity with different names."""
        if len(items) <= 1:
            return items

        names = [item["name"] for item in items]
        merge_map = {}  # index -> canonical_index

        for i, name_i in enumerate(names):
            for j, name_j in enumerate(names):
                if i >= j:
                    continue
                if self._is_same_entity(name_i, name_j):
                    # Prefer shorter name unless it's pure acronym and other is descriptive
                    canonical_idx = i if len(name_i) <= len(name_j) else j
                    other_idx = j if canonical_idx == i else i
                    merge_map[other_idx] = canonical_idx

        # Build result, skipping merged items
        seen = set()
        result = []
        for idx, item in enumerate(items):
            if idx in merge_map:
                canonical_idx = merge_map[idx]
                # Merge descriptions if canonical is shorter
                canonical_item = items[canonical_idx]
                if len(item.get("description", "")) > len(canonical_item.get("description", "")):
                    canonical_item["description"] = item["description"]
                continue
            if idx in seen:
                continue
            seen.add(idx)
            result.append(item)
        return result

    def _is_same_entity(self, a: str, b: str) -> bool:
        """Detect if two names refer to the same entity."""
        a_lower = a.lower().strip()
        b_lower = b.lower().strip()

        if a_lower == b_lower:
            return True

        # Check acronym match: e.g., "DIFFCOT" matches "Diffusion-styled Chain of Thought"
        def get_acronym(text):
            words = text.replace("-", " ").split()
            letters = [w[0] for w in words if w[0].isalpha()]
            return "".join(letters).lower()

        a_acro = get_acronym(a_lower)
        b_acro = get_acronym(b_lower)

        # One is acronym of the other
        if len(a) <= len(b) * 0.4 and a_acro and (a_lower == b_acro or a_lower in b_acro):
            return True
        if len(b) <= len(a) * 0.4 and b_acro and (b_lower == a_acro or b_lower in a_acro):
            return True

        # High Jaccard similarity (near-identical names)
        score = self._jaccard(a_lower, b_lower)
        if score > 0.85:
            return True

        # Substring containment with high overlap
        if a_lower in b_lower or b_lower in a_lower:
            shorter, longer = (a_lower, b_lower) if len(a_lower) < len(b_lower) else (b_lower, a_lower)
            if len(shorter) >= len(longer) * 0.6:
                return True

        return False

    async def resolve(self, raw_name: str, entity_type: str) -> str:
        key = raw_name.lower().strip().rstrip(".,;")

        # 1. Exact match
        if key in self.aliases:
            return self.aliases[key]
        if key in self.learned:
            return self.learned[key]

        combined = {**self.aliases, **self.learned}

        # 2. Word-boundary-aware substring match (avoid short-alias false positives)
        key_words = set(key.split())
        for alias, canonical in combined.items():
            alias_words = set(alias.split())
            # Require at least one shared word OR high character overlap
            if key_words & alias_words:
                # If they share words, check if one is a clear substring of the other
                if key == alias:
                    return canonical
                if key in alias and len(key) >= len(alias) * 0.6:
                    return canonical
                if alias in key and len(alias) >= len(key) * 0.6:
                    return canonical
            else:
                # No shared words: only allow exact match or very high Jaccard
                if key == alias:
                    return canonical

        # 3. Fuzzy similarity match
        if self.entity_vectors and len(self.entity_vectors) > 0:
            best = self._string_similarity_match(key)
            if best:
                return best

        self.entity_vectors[raw_name] = await self._embed(raw_name)
        return raw_name

    def _string_similarity_match(self, key: str) -> str:
        best = None
        best_score = 0.0
        for canonical in self.entity_vectors:
            score = self._jaccard(key, canonical.lower())
            if score > best_score and score > 0.7:
                best_score = score
                best = canonical
        return best

    def _jaccard(self, a: str, b: str) -> float:
        sa, sb = set(a.split()), set(b.split())
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    async def _embed(self, text: str) -> List[float]:
        return [0.0] * 768

    def confirm_merge(self, raw_name: str, canonical: str):
        self.learned[raw_name.lower().strip()] = canonical
        self._save_learned()

    def get_review_queue(self) -> List[Dict]:
        return self.review_queue
