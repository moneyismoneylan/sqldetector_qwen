from sqldetector.fuzz import bytefuzz


def test_payloads_include_nul():
    payloads = bytefuzz.generate_payloads()
    assert b"\x00" in payloads
