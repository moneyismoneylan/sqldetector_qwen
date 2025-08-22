from sqldetector.modules.waf import learn

def fake_send(payload: str) -> str:
    # mimic gateway turning '+' into space
    return payload.replace("+", " ")

def test_waf_learn_matrix():
    matrix = learn.learn(fake_send)
    assert matrix["1+1"] == "1 1"
