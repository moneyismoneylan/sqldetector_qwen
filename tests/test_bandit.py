from sqldetector.detect.bandit import UCB1Planner


def test_ucb1_planner_prefers_best_arm():
    planner = UCB1Planner(["a", "b"])
    arm1 = planner.select_arm()
    planner.update(arm1, 1.0)  # reward for first arm
    arm2 = planner.select_arm()
    planner.update(arm2, 0.0)  # poor reward for second arm
    # After initial exploration, the planner should prefer arm 'a'
    for _ in range(5):
        assert planner.select_arm() == "a"
        planner.update("a", 1.0)


def test_ucb1_prune_removes_bad_arm():
    planner = UCB1Planner(["a", "b"])
    for _ in range(3):
        planner.update("b", 0.0)
    planner.prune(min_pulls=3, threshold=0.1)
    assert "b" not in planner.arms
