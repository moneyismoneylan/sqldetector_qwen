from sqldetector.smart.waf.adaptive import AdaptiveEngine


def test_waf_downshift_and_recover():
    eng = AdaptiveEngine(level="stealth")
    assert eng.mode == "fast"
    eng.observe({"status": 429, "headers": {}})
    assert eng.mode == "stealth"
    eng.observe({"status": 200, "headers": {}})
    assert eng.mode == "fast"
    assert any(e.reason.startswith("downshift") for e in eng.timeline)
