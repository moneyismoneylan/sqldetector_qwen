from sqldetector.smart.evidence.poc import build_snippets


def test_poc_contains_snippets(tmp_path):
    data = build_snippets(
        "http://example", {"q": "1"}, {"q": "1'"},
        {"status": 200, "len": 10, "time": 0.1},
        {"status": 500, "len": 20, "time": 0.2},
        outdir=tmp_path,
    )
    assert "curl" in data and "requests" in data and "postman" in data
    assert (tmp_path / "postman.json").exists()
