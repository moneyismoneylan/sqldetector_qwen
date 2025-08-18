from sqldetector.plugin_registry import get, register
import importlib


def test_register_and_get():
    def dummy():
        return True

    register("demo", "dummy", dummy)
    plugins = get("demo")
    assert "dummy" in plugins and plugins["dummy"] is dummy


def test_sample_plugins_loaded():
    importlib.import_module("sqldetector.plugins.db.mysql_basic")
    importlib.import_module("sqldetector.plugins.waf.cloudflare_basic")
    assert "mysql_basic" in get("db")
    assert "cloudflare_basic" in get("waf")
