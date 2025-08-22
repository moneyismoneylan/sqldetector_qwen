from sqldetector.auth import token_freeze


def test_extract_tokens():
    html = '<form><input type="hidden" name="csrf_token" value="abc"></form>'
    tokens = token_freeze.extract_tokens(html)
    assert tokens["csrf_token"] == "abc"
