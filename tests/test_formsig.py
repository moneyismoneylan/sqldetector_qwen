from sqldetector.dedupe.formsig import form_signature


def test_formsig_normalises_fields():
    f1 = form_signature("/login", [("user", "text"), ("pass", "password")])
    f2 = form_signature("/login", [("pass", "password"), ("user", "text")])
    assert f1 == f2
