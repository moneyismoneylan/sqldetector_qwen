from sqldetector.validation.differential import significant_timing_delta


def test_significant_delta():
    assert significant_timing_delta([0.1, 0.1], [0.3, 0.3], threshold=0.1)
    assert not significant_timing_delta([0.1, 0.11], [0.12, 0.11], threshold=0.1)
