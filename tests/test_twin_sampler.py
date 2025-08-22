from sqldetector.timing import twin_sampler


def test_sample_median():
    calls = iter([0.1, 0.2, 0.15])
    def fake_ping():
        return next(calls)
    assert twin_sampler.sample(fake_ping) == 0.15
