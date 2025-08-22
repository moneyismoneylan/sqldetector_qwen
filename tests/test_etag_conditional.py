from sqldetector.modules.crawl import etag

def test_etag_cache():
    cache = etag.ETagCache()
    assert cache.should_fetch("/a", "v1")
    assert not cache.should_fetch("/a", "v1")
    assert cache.should_fetch("/a", "v2")
