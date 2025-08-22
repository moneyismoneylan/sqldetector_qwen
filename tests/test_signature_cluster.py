from sqldetector.modules.cluster import signature

def test_signature_cluster():
    data = [
        {"status": 200, "body": "ok"},
        {"status": 404, "body": "missing"},
        {"status": 200, "body": "ok"},
    ]
    clusters = signature.cluster(data)
    assert len(clusters) == 2
