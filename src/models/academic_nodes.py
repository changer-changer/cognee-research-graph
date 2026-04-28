from typing import List, Optional, Dict, Any
from pydantic import Field, model_validator
import sys
sys.path.insert(0, '/home/cuizhixing/cognee-env/lib/python3.10/site-packages')
from cognee.infrastructure.engine import DataPoint


class Paper(DataPoint):
    """学术论文节点 - 使用title作为name用于显示和去重"""
    name: str = Field(default="", description="Display name, auto-set from title")
    title: str
    authors: List[str] = []
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    abstract: str = ""
    metadata: Dict[str, Any] = {
        "index_fields": ["title", "abstract"],
        "identity_fields": ["title"],
    }

    @model_validator(mode="after")
    def set_name_from_title(self) -> "Paper":
        if not self.name:
            self.name = self.title[:100]
        return self


class Method(DataPoint):
    """方法/技术/基准测试节点"""
    name: str = Field(description="Standard short name, e.g., LoRA, BERT, ChaosBench-Logic")
    description: str = ""
    method_type: str = "unknown"
    metadata: Dict[str, Any] = {
        "index_fields": ["name", "description"],
        "identity_fields": ["name"],
    }


class Problem(DataPoint):
    """问题/任务节点"""
    name: str = Field(description="Standard problem name, e.g., Machine Translation")
    description: str = ""
    problem_level: str = "task"
    parent: Optional["Problem"] = None
    metadata: Dict[str, Any] = {
        "index_fields": ["name", "description"],
        "identity_fields": ["name"],
    }


class Insight(DataPoint):
    """洞察/发现节点 - 使用statement摘要作为name"""
    name: str = Field(default="", description="Display name, auto-set from statement")
    statement: str = Field(description="Cognitive increment statement, not a summary")
    insight_type: str = "empirical_finding"
    confidence: str = "medium"
    evidence_quote: str = ""
    from_paper: Optional[Paper] = None
    metadata: Dict[str, Any] = {
        "index_fields": ["statement"],
        "identity_fields": ["statement"],
    }

    @model_validator(mode="after")
    def set_name_from_statement(self) -> "Insight":
        if not self.name:
            self.name = self.statement[:80] + ("..." if len(self.statement) > 80 else "")
        return self


class Resource(DataPoint):
    """资源/数据集/工具节点"""
    name: str
    resource_type: str = "dataset"
    description: str = ""
    metadata: Dict[str, Any] = {
        "index_fields": ["name"],
        "identity_fields": ["name"],
    }


class PaperRelations(DataPoint):
    """论文关系容器 - 关联论文与其方法/问题/资源/洞察"""
    name: str = Field(default="", description="Display name, auto-set from paper title")
    paper: Paper
    proposes: Optional[List[Method]] = None
    uses: Optional[List[Method]] = None
    addresses: Optional[List[Problem]] = None
    evaluates_on: Optional[List[Resource]] = None
    contains_insight: Optional[List[Insight]] = None
    metadata: Dict[str, Any] = {
        "index_fields": ["name"],
        "identity_fields": ["name"],
    }

    @model_validator(mode="after")
    def set_name_from_paper(self) -> "PaperRelations":
        if not self.name and self.paper:
            self.name = f"rels_of_{self.paper.title[:60]}"
        return self


class ProblemRelations(DataPoint):
    """问题关系容器 - 存储问题层级关系"""
    name: str = Field(default="", description="Display name, auto-set from problem name")
    problem: Problem
    is_subtask_of: Optional[List[Problem]] = None  # child -> parent
    metadata: Dict[str, Any] = {
        "index_fields": ["name"],
        "identity_fields": ["name"],
    }

    @model_validator(mode="after")
    def set_name_from_problem(self) -> "ProblemRelations":
        if not self.name and self.problem:
            self.name = f"rels_of_{self.problem.name[:60]}"
        return self


class MethodRelations(DataPoint):
    """方法关系容器 - 关联方法与其他方法/问题"""
    name: str = Field(default="", description="Display name, auto-set from method name")
    method: Method
    # Method -> Method hierarchical relations
    contains: Optional[List[Method]] = None          # parent contains child component/sub-method
    uses_technique: Optional[List[Method]] = None    # method uses a technique as sub-component
    # Method -> Method peer relations
    improves_upon: Optional[List[Method]] = None
    is_variant_of: Optional[List[Method]] = None
    combines: Optional[List[Method]] = None
    # Method -> Problem relations
    solves: Optional[List[Problem]] = None
    partially_solves: Optional[List[Problem]] = None
    metadata: Dict[str, Any] = {
        "index_fields": ["name"],
        "identity_fields": ["name"],
    }

    @model_validator(mode="after")
    def set_name_from_method(self) -> "MethodRelations":
        if not self.name and self.method:
            self.name = f"rels_of_{self.method.name[:60]}"
        return self
