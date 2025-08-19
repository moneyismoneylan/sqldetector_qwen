from sqldetector.detect.timing_stats import evaluate_timing, sequential_test


def test_evaluate_timing_detects_difference():
    control = [0.1, 0.11, 0.09, 0.1, 0.1]
    variant = [0.3, 0.31, 0.29, 0.28, 0.32]
    result = evaluate_timing(control, variant)
    assert result["p"] < 0.05
    assert abs(result["cliffs_delta"]) > 0.9


def test_sequential_test_stops_early():
    control_vals = iter([0.1, 0.1, 0.1, 0.1, 0.1])
    variant_vals = iter([0.3, 0.3, 0.3, 0.3, 0.3])

    def next_control():
        return next(control_vals)

    def next_variant():
        return next(variant_vals)

    detected, stats = sequential_test(next_control, next_variant, max_rounds=5, alpha=0.05)
    assert detected
    assert stats["rounds"] < 5
