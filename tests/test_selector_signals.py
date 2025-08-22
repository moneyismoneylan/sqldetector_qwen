from sqldetector.autopilot.selector import classify_target
from sqldetector.autopilot import policy


class DummyResp:
    def __init__(self, headers, text=""):
        self.headers = headers
        self.text = text


class DummyClient:
    def __init__(self, headers, body):
        self._headers = headers
        self._body = body

    def head(self, url, timeout=5):
        return DummyResp(self._headers)

    def get(self, url, timeout=8):
        return DummyResp(self._headers, self._body)


def test_api_classification():
    client = DummyClient({"Content-Type": "application/json"}, "{}")
    profile = classify_target("http://example", client, {"cores": 4, "ram_gb": 8})
    assert profile["kind"] == "api-json"
    assert policy.choose_preset(profile) == "api"


def test_forms_classification():
    body = "<html><form></form><form></form><form></form></html>"
    client = DummyClient({"Content-Type": "text/html"}, body)
    profile = classify_target("http://example", client, {"cores": 4, "ram_gb": 8})
    assert profile["kind"] == "forms-heavy"
    assert policy.choose_preset(profile) == "forms"
