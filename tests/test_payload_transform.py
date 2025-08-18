import random

from sqldetector.payload.transform import randomize, batch_randomize


def test_randomize_changes_case_and_comment():
    rng = random.Random(0)
    payload = "select * from users"
    out = randomize(payload, rng=rng)
    assert out.endswith("#")  # with seed 0 the first choice is '#'
    assert out[:-1] != payload  # case changed


def test_batch_randomize_iterable():
    rng = random.Random(1)
    payloads = list(batch_randomize(["a", "b"], rng=rng))
    assert len(payloads) == 2
    assert payloads[0] != "a"
