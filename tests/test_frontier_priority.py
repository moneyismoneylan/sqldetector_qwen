from sqldetector.core.config import Settings
from sqldetector.discovery.frontier import Frontier


def test_frontier_priority_order():
    f = Frontier(Settings())
    f.add("http://x/a.json")
    f.add("http://x/form/login")
    f.add("http://x/api/users")
    f.add("http://x/index.html")
    order = [f.pop() for _ in range(4)]
    assert "form" in order[0]
    assert "/api" in order[1]
    assert "json" in order[2]
