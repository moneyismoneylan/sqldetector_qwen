from sqldetector.presets import load_preset


def test_turbo_preset_values():
    preset = load_preset("turbo")["sqldetector"]
    assert preset["max_connections"] >= 100
    assert preset["hedge_enabled"] is True
