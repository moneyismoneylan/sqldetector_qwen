from sqldetector.modules.importers import openapi, postman, har
from pathlib import Path

def fixture(name):
    return Path("tests/fixtures") / name

def test_openapi_import():
    eps = openapi.load(str(fixture("openapi.json")))
    assert {e["url"] for e in eps} == {"/users", "/items"}

def test_postman_import():
    eps = postman.load(str(fixture("postman.json")))
    assert len(eps) == 2

def test_har_import():
    eps = har.load(str(fixture("sample.har")))
    assert len(eps) == 2
