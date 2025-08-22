from sqldetector.fuzz import hpp


def test_generate_variants():
    variants = hpp.generate_variants("id", "1")
    assert ("id", ["1", "1"]) in variants
    assert any(name.startswith("id") for name, _ in variants)
