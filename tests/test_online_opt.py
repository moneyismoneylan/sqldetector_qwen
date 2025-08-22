from sqldetector.optimizer.online import OnlineOptimizer


def test_decide_next_families():
    opt = OnlineOptimizer()
    opt.record("fam1", True, 100)
    opt.record("fam1", False, 100)
    opt.record("fam2", False, 50)
    order = opt.decide_next_families(150)
    assert order[0] == "fam1"
    assert set(order) == {"fam1", "fam2"}
