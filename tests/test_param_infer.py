from sqldetector.modules.params import infer

def test_param_infer_numeric():
    assert infer.infer("age", "42") == "numeric"


def test_param_infer_slug():
    assert infer.infer("slug", "abc-def") == "slug"
