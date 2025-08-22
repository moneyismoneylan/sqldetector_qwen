from sqldetector.presets import load_preset, deep_merge


def test_user_overrides_preset():
    preset = load_preset("fast")["sqldetector"]
    base = {"max_connections": 5}
    merged = deep_merge(preset, base)
    assert merged["max_connections"] == 5


def test_nested_merge():
    base = {"retry_budget": {"total": 1}}
    override = {"retry_budget": {"per_host": 2}}
    merged = deep_merge(base, override)
    assert merged["retry_budget"]["total"] == 1
    assert merged["retry_budget"]["per_host"] == 2
