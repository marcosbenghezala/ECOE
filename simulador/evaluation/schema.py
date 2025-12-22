from typing import Any, Dict, List, TypedDict


class ScoreBlock(TypedDict):
    score: int
    max: int
    percentage: float


class EvaluationBlockItem(TypedDict):
    id: str
    text: str
    done: bool
    score: int
    max_score: int
    critical: bool
    evidence: List[Dict[str, Any]]


class EvaluationBlock(TypedDict):
    id: str
    name: str
    score: int
    max: int
    percentage: float
    items: List[EvaluationBlockItem]


class EvaluationResult(TypedDict):
    schema_version: str
    timestamp: str
    case: Dict[str, Any]
    scores: Dict[str, Any]
    blocks: List[EvaluationBlock]
    development: Dict[str, Any]
    survey: Dict[str, Any]
    debug: Dict[str, Any]
    legacy: Dict[str, Any]
