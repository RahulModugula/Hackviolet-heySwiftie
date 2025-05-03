"""Knowledge graph for fact relationships."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FactNode:
    """Node in knowledge graph."""

    id: str
    content: str
    type: str  # "fact" | "entity" | "concept"
    metadata: dict = field(default_factory=dict)


@dataclass
class Relationship:
    """Edge between facts."""

    source_id: str
    target_id: str
    relation_type: str  # "related_to" | "supports" | "contradicts"
    strength: float  # 0-1


class KnowledgeGraph:
    """Graph-based knowledge representation."""

    def __init__(self, memory_manager):
        self.memory = memory_manager
        self.nodes: dict[str, FactNode] = {}
        self.relationships: list[Relationship] = []

    def add_fact(self, fact_id: str, content: str, fact_type: str = "fact") -> FactNode:
        """Add a fact node."""
        node = FactNode(id=fact_id, content=content, type=fact_type)
        self.nodes[fact_id] = node
        return node

    def relate(self, source_id: str, target_id: str, relation: str, strength: float = 0.8):
        """Create relationship between facts."""
        self.relationships.append(
            Relationship(
                source_id=source_id, target_id=target_id, relation_type=relation, strength=strength
            )
        )

    def get_related_facts(self, fact_id: str, depth: int = 2) -> list[str]:
        """Get related facts using graph traversal."""
        visited = set()
        to_visit = [fact_id]
        related = []

        for _ in range(depth):
            next_visit = []
            for node_id in to_visit:
                if node_id in visited:
                    continue
                visited.add(node_id)

                # find connected nodes
                for rel in self.relationships:
                    if rel.source_id == node_id and rel.target_id not in visited:
                        next_visit.append(rel.target_id)
                        related.append(rel.target_id)
                    elif rel.target_id == node_id and rel.source_id not in visited:
                        next_visit.append(rel.source_id)
                        related.append(rel.source_id)

            to_visit = next_visit

        return related

    def build_from_facts(self):
        """Build graph from extracted semantic facts."""
        facts = self.memory.get_user_facts()

        for fact in facts:
            fact_id = fact.key
            self.add_fact(
                fact_id,
                str(fact),
                fact_type="fact",
            )

        # relate facts with common subjects
        fact_list = list(self.nodes.keys())
        for i, fact1_id in enumerate(fact_list):
            for fact2_id in fact_list[i + 1 :]:
                # simple heuristic: same subject = related
                if self.nodes[fact1_id].content.split()[0] == self.nodes[fact2_id].content.split()[0]:
                    self.relate(fact1_id, fact2_id, "related_to", strength=0.7)
