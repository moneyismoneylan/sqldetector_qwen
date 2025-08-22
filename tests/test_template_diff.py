from sqldetector.diff import template


def test_diff_dynamic():
    old = "<html><body><div>static</div></body></html>"
    new = "<html><body><div>dynamic</div></body></html>"
    a, b = template.diff_dynamic(old, new)
    assert a != b
    assert "dynamic" not in a
