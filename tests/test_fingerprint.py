from sqldetector.fingerprint.rag import FingerprintIndex
import xxhash


def test_fingerprint_lookup():
    headers = {'a': 'b'}
    key = xxhash.xxh3_64_hexdigest('a:b')
    fi = FingerprintIndex({key: 'db'})
    assert fi.lookup(headers) == 'db'
