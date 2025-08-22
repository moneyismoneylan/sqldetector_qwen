import argparse
import sys
from urllib.parse import urlparse

from sqldetector.planner import pipeline
from sqldetector.core.config import Settings, merge_settings
from sqldetector.presets import (
    load_preset,
    deep_merge as merge_dicts,
    apply_system_overrides,
)
from sqldetector.autopilot import selector, policy, system as autosys, store


def main(argv=None):
    parser = argparse.ArgumentParser(description="AI-powered SQL injection detector")
    parser.add_argument("url", help="Target URL")
    parser.add_argument("--dry-run", action="store_true", help="Run pipeline without network calls")
    parser.add_argument("--config", type=str, help="Path to TOML configuration file")
    parser.add_argument("--trace-dir", type=str, help="Directory to store trace logs")
    parser.add_argument(
        "--preset",
        choices=["fast","stealth","api","spa","forms","crawler","budget-ci"],
        help="Use built-in preset",
    )
    parser.add_argument("--auto", action="store_true", help="Enable AutoPilot mode")
    parser.add_argument("--autopilot", action="store_true", help="Alias for --auto")
    parser.add_argument("--print-plan", action="store_true", help="Print AutoPilot plan and exit if --dry-run")
    parser.add_argument("--force-preset", type=str, help="Force preset name in AutoPilot mode")
    parser.add_argument(
        "--stop-after-first-finding", action="store_true", help="Exit on first finding",
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
    parser.add_argument("--bandit", choices=["off", "ucb1", "thompson"], help="Payload bandit algorithm")
    parser.add_argument("--dns-cache-ttl", type=int, dest="dns_cache_ttl", help="DNS cache TTL seconds")
    parser.add_argument("--prewarm", action="store_true", help="Pre-warm HTTP connections")
    parser.add_argument("--happy-eyeballs", action="store_true", help="Enable Happy Eyeballs dialer")
    parser.add_argument("--range-fetch-kb", type=int, help="Partial body fetch size in KB")
    parser.add_argument("--simhash", action="store_true", help="Enable simhash dedupe")
    parser.add_argument("--near-dup-th", type=int, dest="near_dup_th", help="Simhash Hamming distance threshold")
    parser.add_argument("--form-dedupe", action="store_true", help="Enable form schema dedupe")
    parser.add_argument("--server-weighting", action="store_true", help="Weight payloads by server fingerprint")
    parser.add_argument("--endpoint-budget-ms", type=int, help="Per-endpoint time budget in ms")
    parser.add_argument("--bloom", action="store_true", help="Enable persistent bloom skiplist")
    parser.add_argument("--bloom-bits", type=int, help="Bloom filter size in bits")
    parser.add_argument("--bloom-ttl", type=int, help="Bloom filter TTL hours")
    parser.add_argument("--cpu-target-pct", type=int, help="CPU usage target percentage")
    parser.add_argument("--cpu-pacer-min-rps", type=int, help="Minimum pacer rate")
    parser.add_argument("--cpu-pacer-max-rps", type=int, help="Maximum pacer rate")

    # SMART mode flags (opt-in)
    parser.add_argument("--smart", action="store_true", help="Enable SMART mode")
    parser.add_argument("--poc", action="store_true", help="Generate explainable PoC artifacts")
    parser.add_argument("--fusion", action="store_true", help="Enable signal fusion")
    parser.add_argument("--waf-adapt", action="store_true", help="Enable WAF-adaptive engine")
    parser.add_argument("--oob", action="store_true", help="Enable out-of-band checks")
    parser.add_argument("--xhr-map", action="store_true", help="Map client-side XHR/fetch flows")
    parser.add_argument("--dbms-fp", action="store_true", help="DBMS fingerprinting and robust timing")
    parser.add_argument("--flow-sm", action="store_true", help="Multi-step flow state machine")
    parser.add_argument("--dedupe-adv", action="store_true", help="Advanced SimHash/FormSig++ dedupe")
    parser.add_argument("--kg", action="store_true", help="Endpoint-param knowledge graph")
    parser.add_argument("--remediate", action="store_true", help="Developer remediation tips")
    parser.add_argument("--lang", choices=["tr", "en"], default="tr", help="Narration language")
    parser.add_argument("--report", choices=["json", "html", "all"], default="all", help="Report format")
    parser.add_argument("--no-consent", action="store_true", help="Skip SMART mode consent notice")
    parser.add_argument("--unsafe-artifacts", action="store_true", help="Do not redact secrets in PoC artifacts")
    # advanced CLI surface
    parser.add_argument("--import-openapi", dest="import_openapi", help="Import targets from OpenAPI schema")
    parser.add_argument("--import-postman", dest="import_postman", help="Import targets from Postman collection")
    parser.add_argument("--import-har", dest="import_har", help="Import targets from HAR file")
    parser.add_argument("--graphql", action="store_true", help="Enable GraphQL fuzz")
    parser.add_argument("--grpc", action="store_true", help="Enable gRPC fuzz")
    parser.add_argument("--param-infer", action="store_true", help="Enable parameter type inference")
    parser.add_argument("--waf-learn", action="store_true", help="Learn WAF normalization")
    parser.add_argument("--ratelimit-auto", action="store_true", help="Auto rate-limit zoning")
    parser.add_argument("--tls-fp", choices=["auto", "browser", "default"], help="TLS/JA3 fingerprinting")
    parser.add_argument("--http3", action="store_true", help="Attempt HTTP/3/QUIC")
    parser.add_argument("--cdn-aware", action="store_true", help="CDN vs origin routing")
    parser.add_argument("--oauth", dest="oauth", help="OAuth/OIDC flow file")
    parser.add_argument("--layer-split-tests", action="store_true", help="Parser-layer discrepancy tests")
    parser.add_argument("--payload-cfg", dest="payload_cfg", help="Grammar-based payload config")
    parser.add_argument("--delta-debug", action="store_true", help="Minimal PoC reduction")
    parser.add_argument("--route-calibrate", action="store_true", help="Per-route timing calibration")
    parser.add_argument("--cluster-endpoints", action="store_true", help="Response signature clustering")
    parser.add_argument("--ci-diff", nargs=2, metavar=("BASELINE_A", "BASELINE_B"), help="CI diff run")
    parser.add_argument("--js-extract", action="store_true", help="JS/source-map endpoint mining")
    parser.add_argument("--etag-conditional", action="store_true", help="Conditional crawl using ETag")
    parser.add_argument("--encoding-adapt", action="store_true", help="Accept-Encoding adaptation")
    parser.add_argument("--sticky-session", action="store_true", help="Load balancer affinity")
    parser.add_argument("--replay", dest="replay", help="Replay assist from capture file")
    parser.add_argument("--otel", choices=["off", "console", "otlp"], default="off", help="OpenTelemetry exporter")
    parser.add_argument("--online-optimizer", action="store_true", help="Risk-time optimizer")
    parser.add_argument("--second-order", action="store_true", help="Delayed/second-order detector")
    parser.add_argument("--hpp", action="store_true", help="Parameter pollution tests")
    parser.add_argument("--byte-fuzz", action="store_true", help="Encoding/byte-level fuzz")
    parser.add_argument("--method-override", action="store_true", help="X-HTTP-Method-Override tests")
    parser.add_argument("--cache-bypass", action="store_true", help="Cache bust & origin forcing")
    parser.add_argument("--token-freeze", action="store_true", help="CSRF/anti-bot token capture")
    parser.add_argument("--template-diff", action="store_true", help="Boilerplate stripping diffs")
    parser.add_argument("--l10n-payloads", action="store_true", help="Locale-aware payloads")
    parser.add_argument("--sigv4", type=str, help="Request signing (AWS HMAC) support")
    parser.add_argument("--captcha-aware", action="store_true", help="Pause on captcha challenges")
    parser.add_argument("--honeypot-guard", action="store_true", help="Detect tarpits/honeypots")
    parser.add_argument("--shadow-param", action="store_true", help="Hidden parameter hints")
    parser.add_argument("--safe-poc", action="store_true", help="Idempotent PoC generation")
    parser.add_argument("--subdomain-seed", action="store_true", help="Robots/sitemap subdomain miner")
    parser.add_argument("--locale-shard", action="store_true", help="Accept-Language shard tests")
    parser.add_argument("--twin-sampler", action="store_true", help="Redundant A/B/A timing sampler")
    parser.add_argument("--header-mutator", action="store_true", help="Adaptive header mutator")
    parser.add_argument("--csv-import", action="store_true", help="CSV upload SQLi tests")
    parser.add_argument("--micro", action="store_true", help="Single-thread tiny payload core")

    args = parser.parse_args(argv)

    if args.autopilot:
        args.auto = True

    if args.smart and not args.no_consent:
        from pathlib import Path

        consent_file = Path.home() / ".sqldetector_smart_consent"
        if not consent_file.exists():
            print("Bu aracı yalnızca yetkili testlerde kullanın.")
            consent_file.write_text("ok")

    if args.smart:
        from sqldetector.ui.narrate import Narrator

        narrator = Narrator(lang=args.lang)
        narrator.step("Hedef profili çıkarılıyor…")
        # light-weight pre-scan hooks
        if args.import_openapi:
            narrator.step("OpenAPI içe aktarılıyor…" if args.lang == "tr" else "Importing OpenAPI…")
            try:
                from sqldetector.modules.importers import openapi as imp_openapi

                imp_openapi.load(args.import_openapi)
            except Exception:
                narrator.warn("OpenAPI import failed")
        if args.import_postman:
            narrator.step("Postman içe aktarılıyor…" if args.lang == "tr" else "Importing Postman…")
            try:
                from sqldetector.modules.importers import postman as imp_postman

                imp_postman.load(args.import_postman)
            except Exception:
                narrator.warn("Postman import failed")
        if args.import_har:
            narrator.step("HAR içe aktarılıyor…" if args.lang == "tr" else "Importing HAR…")
            try:
                from sqldetector.modules.importers import har as imp_har

                imp_har.load(args.import_har)
            except Exception:
                narrator.warn("HAR import failed")
        if args.waf_learn:
            narrator.note("WAF sinyali tespit edildi, stealth moduna iniliyor." if args.lang == "tr" else "Learning WAF normalization")
        if args.param_infer:
            try:
                from sqldetector.modules.params import infer as p_infer

                p_infer.infer("id", "1")
            except Exception:
                pass

    settings = merge_settings(args)
    cfg = settings.__dict__

    if args.preset:
        preset_cfg = load_preset(args.preset).get("sqldetector", {})
        cfg = merge_dicts(preset_cfg, cfg)

    if args.auto:
        sysinfo = autosys.detect_system()
        domain = urlparse(args.url).hostname or args.url
        client = None
        try:
            import requests  # type: ignore

            client = requests.Session()
        except Exception:
            pass
        if client is None:
            print("AutoPilot requires the requests package", file=sys.stderr)
            return 1
        try:
            profile = selector.classify_target(args.url, client, sysinfo)
        except Exception:
            print("AutoPilot: unable to reach target", file=sys.stderr)
            return 1
        preset_name = args.force_preset or policy.choose_preset(profile)
        preset_cfg = load_preset(preset_name).get("sqldetector", {})
        cfg = merge_dicts(preset_cfg, cfg)
        cfg = apply_system_overrides(cfg, sysinfo, profile.get("rtt_ms"))
        store.save(domain, profile, preset_name)
        if args.print_plan:
            print(f"AutoPilot selected: {preset_name} (signals: {profile['signals']})")
            if args.dry_run:
                return 0
        settings = Settings(**cfg)
        print(
            f"AutoPilot selected: {preset_name} (signals: {profile['signals']})",
            file=sys.stderr,
        )
    else:
        sysinfo = autosys.detect_system()
        cfg = apply_system_overrides(cfg, sysinfo, None)
        settings = Settings(**cfg)

    if sys.platform != "win32":  # pragma: no cover - best effort
        try:
            import uvloop  # type: ignore

            uvloop.install()
        except Exception:
            pass

    return pipeline.run(args.url, dry_run=args.dry_run, settings=settings)


if __name__ == "__main__":
    main()
