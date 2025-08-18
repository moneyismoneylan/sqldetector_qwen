from sqldetector.filter.bloom import BloomFilter


def test_bloom_filter_detects_duplicates():
    bf = BloomFilter(size=32, hashes=2)
    assert bf.add("foo") is False
    assert bf.add("foo") is True
