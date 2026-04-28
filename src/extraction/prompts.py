PAPER_META_BLOCK = """You are analyzing the following paper:

Title: {paper_title}
Authors: {authors}
Abstract: {abstract}
"""


EXTRACTION_PROMPT_1A = """{paper_meta}

## YOUR TASK

Read the INTRODUCTION, METHOD, and EXPERIMENTS sections below. Extract ONLY what THIS paper ORIGINALLY proposes, designs, or significantly adapts. Do NOT extract methods merely mentioned as background, Related Work, or baselines.

**Section context**: The text below includes Introduction, Method details, and the beginning of Experiments (where datasets and benchmarks are typically listed).

## ENTITY TYPES

1. **Method**: A technique, model, architecture, or algorithm that THIS paper ORIGINALLY proposes as its core contribution.
   - Extract ONLY the top-level framework/system (typically 1 per paper).
   - Do NOT extract sub-components here — they belong in Stage 1b.
   - Do NOT extract existing methods used only as baselines.
   - Use the SHORTEST canonical name from the paper text.
   - **NORMALIZATION**: If the paper introduces both a full name and an acronym (e.g., "Diffusion-styled Chain of Thought (DIFFCOT)"), use ONLY the acronym/short form.
   - Do NOT use vague names like "our proposed method" or "the baseline".

2. **Problem**: A SPECIFIC research task or challenge that THIS paper directly targets.
   - Extract at 2 levels:
     - **task**: Broad research domain (e.g., "Chain-of-Thought Reasoning")
     - **challenge**: Specific difficulty within that domain (e.g., "Error Accumulation in CoT")
   - Do NOT extract generic domains like "Deep Learning" or "LLMs".

3. **Resource**: Datasets, benchmarks, and evaluation metrics that THIS paper ACTUALLY USES in experiments.
   - **IMPORTANT**: Do NOT include models here. Pre-trained models (e.g., "Qwen3-8B", "LLaMA-3-70B") and baseline methods are **Method** nodes, not Resources.
   - Only include: datasets, benchmark suites, metrics (BLEU, ROUGE, accuracy), and open-source tools.

## RELATION TYPES (use EXACTLY these strings)

- Paper→Method: **proposes** (this paper introduces it) | **uses** (existing baseline/component)
- Paper→Problem: **addresses** (primary target)
- Method→Problem: **solves** | **partially_solves**

## CRITICAL RULES

- You are reading INTRODUCTION and METHOD. Ignore Related Work mentions.
- **proposes** ONLY for the paper's original contribution.
- **uses** ONLY for existing methods applied as baselines or components.
- In relations, use the PAPER TITLE as subject_name: "{paper_title}"
- Do NOT artificially limit the number of entities — extract all that meet the criteria above.
- Do NOT extract techniques merely discussed in Related Work.

## OUTPUT FORMAT

Return STRICT JSON:

{{
  "entities": {{
    "methods": [
      {{"name": "DIFFCOT", "description": "Diffusion-styled Chain-of-Thought framework", "type": "method"}}
    ],
    "problems": [
      {{"name": "Chain-of-Thought Reasoning", "description": "Step-by-step reasoning in LLMs", "level": "task"}},
      {{"name": "Error Accumulation in CoT", "description": "Early mistakes propagating through steps", "level": "challenge"}}
    ],
    "resources": [
      {{"name": "MATH-1", "type": "dataset"}},
      {{"name": "SVAMP", "type": "dataset"}}
    ]
  }},
  "relations": [
    {{"subject_type": "Paper", "subject_name": "{paper_title}", "predicate": "proposes", "object_type": "Method", "object_name": "DIFFCOT", "evidence": "direct quote from text"}},
    {{"subject_type": "Paper", "subject_name": "{paper_title}", "predicate": "addresses", "object_type": "Problem", "object_name": "Error Accumulation in CoT", "evidence": "direct quote from text"}},
    {{"subject_type": "Method", "subject_name": "DIFFCOT", "predicate": "solves", "object_type": "Problem", "object_name": "Error Accumulation in CoT", "evidence": "direct quote from text"}}
  ]
}}

## TEXT

{text}
"""


def get_extraction_prompt_1a(text: str, paper_title: str, authors: str, abstract: str) -> str:
    paper_meta = PAPER_META_BLOCK.format(
        paper_title=paper_title,
        authors=authors,
        abstract=abstract[:500],
    )
    prompt = EXTRACTION_PROMPT_1A.replace("{paper_meta}", paper_meta)
    prompt = prompt.replace("{paper_title}", paper_title[:200])
    prompt = prompt.replace("{text}", text[:8000])
    # Replace remaining template placeholders
    prompt = prompt.replace("{authors}", authors)
    prompt = prompt.replace("{abstract}", abstract[:500])
    return prompt


EXTRACTION_PROMPT_1B = """{paper_meta}

## YOUR TASK

Read the METHOD section below. Extract the INTERNAL structure of the top-level method "{top_level_method}".

## RULES

- Extract ONLY components, techniques, and mechanisms that are NOVEL and CENTRAL to this paper's contribution.
- A sub-method should only be extracted if the paper devotes meaningful discussion to it (not just a passing mention).
- Use SPECIFIC names from the paper text: "Diffusion Sliding-Window Mechanism", not "window mechanism".
- **NORMALIZATION**: If a component is introduced with both full name and acronym, use ONLY the short form.
- Do NOT extract generic algorithmic steps (e.g., "forward pass", "gradient descent") unless the paper explicitly frames them as novel contributions.

## RELATION TYPES (use EXACTLY these strings)

- Method→Method: **contains** (parent contains child component/sub-method)
- Method→Method: **uses_technique** (method uses a technique as sub-component but does not contain it)
- Method→Method: **improves_upon** (explicit performance comparison required)
- Method→Method: **is_variant_of** (direct modification)
- Method→Method: **combines** (integrates distinct techniques)

## CRITICAL RULES

- The top-level method "{top_level_method}" should be the subject of most contains relations.
- **contains** is the MOST IMPORTANT relation for expressing method hierarchy.
- **improves_upon** ONLY with explicit performance comparison in the text.
- Do NOT extract techniques merely discussed in Related Work.

## OUTPUT FORMAT

Return STRICT JSON:

{{
  "sub_methods": [
    {{"name": "Diffusion Sliding-Window Mechanism", "description": "Window-based iterative denoising during CoT generation", "parent_method": "{top_level_method}", "type": "technique"}},
    {{"name": "Reward-ranked Candidate Collection", "description": "Collecting candidates by reward scores for noising", "parent_method": "Step-level Forward Noising", "type": "component"}}
  ],
  "relations": [
    {{"subject_type": "Method", "subject_name": "{top_level_method}", "predicate": "contains", "object_type": "Method", "object_name": "Diffusion Sliding-Window Mechanism", "evidence": "direct quote"}},
    {{"subject_type": "Method", "subject_name": "Step-level Forward Noising", "predicate": "contains", "object_type": "Method", "object_name": "Reward-ranked Candidate Collection", "evidence": "direct quote"}}
  ]
}}

## TEXT

{text}
"""


def get_extraction_prompt_1b(text: str, paper_title: str, authors: str, abstract: str, top_level_method: str) -> str:
    paper_meta = PAPER_META_BLOCK.format(
        paper_title=paper_title,
        authors=authors,
        abstract=abstract[:500],
    )
    prompt = EXTRACTION_PROMPT_1B.replace("{paper_meta}", paper_meta)
    prompt = prompt.replace("{top_level_method}", top_level_method[:200])
    prompt = prompt.replace("{paper_title}", paper_title[:200])
    prompt = prompt.replace("{text}", text[:8000])
    prompt = prompt.replace("{authors}", authors)
    prompt = prompt.replace("{abstract}", abstract[:500])
    return prompt


INSIGHT_PROMPT_V2 = """{paper_meta}

## YOUR TASK

Read the EXPERIMENTS and RESULTS section below. Extract 1-3 key insights.

An insight is what the field **LEARNED** from this paper, not what the paper **DID**.

## INSIGHT TYPES

- **empirical_finding**: Unexpected experimental result or pattern.
- **method_innovation**: New technique enabling previously impossible things.
- **boundary_condition**: WHEN/WHERE a method works or fails.
- **negative_result**: Important disconfirmation of common assumption.
- **theoretical_claim**: Formal or conceptual reframing.

## RULES

- Each insight MUST have a direct supporting quote from the paper.
- Do NOT restate the abstract. Extract the non-obvious claim.
- Confidence: "high" (extensive evidence/proof), "medium" (solid experiments), "low" (discussion/conjecture).

## ASSOCIATION — USE EXACT NAMES FROM THIS LIST

Available methods from this paper:
{method_names}

Available problems from this paper:
{problem_names}

When filling `related_method_names` and `related_problem_names`, you MUST use exact names from the lists above.

## OUTPUT FORMAT

Return STRICT JSON:

{{
  "insights": [
    {{
      "statement": "concise declarative sentence of what was learned",
      "type": "empirical_finding",
      "confidence": "high",
      "evidence_quote": "exact text from paper",
      "from_paper": "{paper_title}",
      "related_method_names": ["DIFFCOT"],
      "related_problem_names": ["Error Accumulation in CoT"]
    }}
  ]
}}

## TEXT

{text}
"""


def get_insight_prompt_v2(text: str, paper_title: str, authors: str, abstract: str, method_names: list, problem_names: list) -> str:
    paper_meta = PAPER_META_BLOCK.format(
        paper_title=paper_title,
        authors=authors,
        abstract=abstract[:500],
    )
    method_list = "\n".join(f"- {m}" for m in method_names) if method_names else "(none extracted)"
    problem_list = "\n".join(f"- {p}" for p in problem_names) if problem_names else "(none extracted)"

    prompt = INSIGHT_PROMPT_V2.replace("{paper_meta}", paper_meta)
    prompt = prompt.replace("{paper_title}", paper_title[:200])
    prompt = prompt.replace("{method_names}", method_list)
    prompt = prompt.replace("{problem_names}", problem_list)
    prompt = prompt.replace("{text}", text[:6000])
    prompt = prompt.replace("{authors}", authors)
    prompt = prompt.replace("{abstract}", abstract[:500])
    return prompt
