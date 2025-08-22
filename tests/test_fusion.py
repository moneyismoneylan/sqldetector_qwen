from sqldetector.smart.signal.fusion import FusionModel


def test_fusion_promotes_combined_signals():
    model = FusionModel()
    low = model.score({"reflection": 0.1})
    high = model.score({"reflection": 0.4, "status": 0.3, "size": 0.3})
    assert low < 0.5
    assert high > low
    assert model.confident({"reflection": 0.5, "status": 0.5, "size": 0.5, "time": 0.5, "header": 0.5})
