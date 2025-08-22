import time

from sqldetector.llm_cache import LLMCache


def test_cache_set_get(tmp_path):
    cache = LLMCache(tmp_path / "cache.sqlite")
    key = LLMCache.make_key("host", "schema", "fam", "model", "v1")
    cache.set(key, b"result")
    assert cache.get(key, ttl_hours=1) == b"result"
    # simulate expiry
    cache.conn.execute("UPDATE kv SET ts=? WHERE k=?", (int(time.time()) - 7200, key))
    cache.conn.commit()
    assert cache.get(key, ttl_hours=1) is None
    cache.close()
