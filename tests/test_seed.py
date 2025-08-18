from sqldetector.analysis.seed import extract_endpoints_from_code, extract_endpoints_from_js, Endpoint


def test_extract_endpoints_from_code():
    code = """
from httpx import Client
c = Client()
resp = c.get('/users')
resp = c.post('/users', json={})
"""
    eps = extract_endpoints_from_code(code)
    assert Endpoint('GET', '/users') in eps
    assert Endpoint('POST', '/users') in eps


def test_extract_endpoints_from_js():
    js = "fetch('/api') ; fetch('/api/items')"
    eps = extract_endpoints_from_js(js)
    assert '/api' in eps and '/api/items' in eps
