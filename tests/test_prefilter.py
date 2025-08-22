from sqldetector.prefilter import cheap_prefilter, should_skip_deep_tests


def test_prefilter_flags_suspicious():
    res = cheap_prefilter("http://example/?id=1 union select", {"id": "1 union select"})
    assert res["score"] >= 0.5
    assert not should_skip_deep_tests(res["score"])


def test_prefilter_allows_innocuous():
    res = cheap_prefilter("http://example/?q=hi", {"q": "hi"})
    assert res["score"] <= 0.2
    assert should_skip_deep_tests(res["score"])
