from sqldetector.filter.dom import ProximityFilter


def test_dom_filter_dedup():
    pf = ProximityFilter()
    assert pf.is_duplicate('http://a', 'x') is False
    assert pf.is_duplicate('http://a/', 'x') is True  # normalized
