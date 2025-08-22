from sqldetector.smart.dedupe.simhash import cluster
from sqldetector.smart.dedupe.formsigpp import form_signature


def test_simhash_clusters_near_dups():
    pages = ["hello world", "hello world ", "completely different"]
    clusters = cluster(pages, thresh=10)
    assert any(len(c) > 1 for c in clusters)


def test_formsigpp_identical():
    sig1 = form_signature("/submit", [{"name": "a", "type": "text", "path": "/f1"}])
    sig2 = form_signature("/submit", [{"name": "a", "type": "text", "path": "/f1"}])
    assert sig1 == sig2
