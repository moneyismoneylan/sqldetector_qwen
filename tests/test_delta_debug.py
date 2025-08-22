from sqldetector.modules.poc import delta

def test_delta_shrink():
    payload = "1 ' OR 1=1 --"
    result = delta.shrink(payload, lambda p: "1=1" in p)
    assert result.strip() == "1=1"
