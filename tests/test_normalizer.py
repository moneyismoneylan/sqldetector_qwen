from sqldetector.detect import normalizer


def test_normalizer_returns_input():
    assert normalizer.normalize("<html>") == "<html>"
