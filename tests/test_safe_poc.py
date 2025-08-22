from sqldetector.poc import safe


def test_build_pair_and_invariant():
    pair = safe.build_pair("http://example.com", "1")
    assert pair.confirm[0] == "POST"
    assert safe.invariant("a", "a")
