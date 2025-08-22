from sqldetector.smart.graph.knowledge import KnowledgeGraph


def test_knowledge_graph_ranking():
    kg = KnowledgeGraph()
    kg.add("/a", "id", "int")
    kg.add("/b", "id", "int")
    kg.add("/a", "name", "str")
    ranking = kg.rank()
    assert ranking[0][0] == "id" and ranking[0][1] == 2
