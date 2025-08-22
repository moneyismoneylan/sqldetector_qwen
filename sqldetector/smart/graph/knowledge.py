from collections import defaultdict, Counter
from typing import Dict, List, Tuple


class KnowledgeGraph:
    """Endpoint-param graph with simple centrality ranking."""

    def __init__(self) -> None:
        self.graph: Dict[str, Dict[str, str]] = defaultdict(dict)

    def add(self, endpoint: str, param: str, ptype: str) -> None:
        self.graph[endpoint][param] = ptype

    def adjacency(self) -> Dict[str, Dict[str, str]]:
        return self.graph

    def rank(self) -> List[Tuple[str, int]]:
        counter: Counter[str] = Counter()
        for _, params in self.graph.items():
            counter.update(params.keys())
        return counter.most_common()
