from sqldetector.presets import apply_system_overrides


def test_low_spec_clamps():
    cfg = {"max_connections": 20, "max_keepalive_connections": 10, "timeout_connect": 8.0, "timeout_read": 15.0}
    sysinfo = {"cores": 2, "ram_gb": 2}
    tuned = apply_system_overrides(cfg, sysinfo, None)
    assert tuned["max_connections"] <= 8
    assert tuned["timeout_read"] <= 10.0
