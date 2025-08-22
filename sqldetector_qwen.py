import argparse
import sys

from sqldetector.planner import pipeline
from sqldetector.core.config import Settings, merge_settings
from sqldetector.presets import (
    apply_system_aware_overrides,
    load_preset,
    merge_config as merge_dicts,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description="AI-powered SQL injection detector")
    parser.add_argument("url", help="Target URL")
    parser.add_argument("--dry-run", action="store_true", help="Run pipeline without network calls")
    parser.add_argument("--config", type=str, help="Path to TOML configuration file")
    parser.add_argument("--trace-dir", type=str, help="Directory to store trace logs")
    parser.add_argument("--preset", choices=["fast"], help="Use built-in preset")
    parser.add_argument(
        "--stop-after-first-finding", action="store_true", help="Exit on first finding"
    )
    parser.add_argument("--max-forms-per-page", type=int)
    parser.add_argument("--max-tests-per-form", type=int)
    parser.add_argument("--use-llm", choices=["auto", "always", "never"])
    parser.add_argument("--log-json", action="store_true", help="Enable JSON structured logging")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    args = parser.parse_args(argv)

    settings = merge_settings(args)

    if args.preset:
        preset_cfg = load_preset(args.preset).get("sqldetector", {})
        settings = Settings(**merge_dicts(settings.__dict__, preset_cfg))

    settings = Settings(**apply_system_aware_overrides(settings.__dict__))

    if sys.platform != "win32":  # pragma: no cover - best effort
        try:
            import uvloop  # type: ignore

            uvloop.install()
        except Exception:
            pass

    return pipeline.run(args.url, dry_run=args.dry_run, settings=settings)


if __name__ == "__main__":
    main()
