from sqldetector.planner.adaptive import AdaptivePlanner


def test_adaptive_planner_updates():
    planner = AdaptivePlanner(['a', 'b'], epsilon=0.0)
    planner.update('a', 1.0)
    assert planner.select_arm() == 'a'
