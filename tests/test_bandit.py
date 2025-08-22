from sqldetector.scheduling.bandit import BanditScheduler


def test_ucb1_deterministic_selection():
    scheduler = BanditScheduler(algo="ucb1")
    families = ["a", "b"]
    host = "example.com"
    endpoint = "/"

    seq = []
    for _ in range(6):
        fam = scheduler.select(host, endpoint, families)
        seq.append(fam)
        reward = 1.0 if fam == "a" else 0.0
        scheduler.update(host, endpoint, fam, reward)

    # first two selections explore both arms, afterwards always 'a'
    assert seq[0] == "a"
    assert seq[1] == "b"
    assert all(f == "a" for f in seq[2:])
