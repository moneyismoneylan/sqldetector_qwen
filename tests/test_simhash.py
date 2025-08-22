from sqldetector.dedupe.simhash import is_near_duplicate, simhash64


def test_simhash_near_duplicate():
    text1 = "<html><body>Hello World!</body></html>"
    text2 = "<html><body>hello   world?</body></html>"
    h1 = simhash64(text1)
    h2 = simhash64(text2)
    assert is_near_duplicate(h1, h2, threshold=6)
