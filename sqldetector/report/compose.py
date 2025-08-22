import json
from pathlib import Path
from typing import Any, Dict

try:  # pragma: no cover - optional dependency
    import orjson  # type: ignore
except Exception:  # pragma: no cover - if orjson missing
    orjson = None  # type: ignore


MINIMAL_CSS = """
body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:2em;}
h1{font-size:1.4em;margin-bottom:0.2em;}section{margin-bottom:1.5em;}pre{background:#f6f8fa;padding:1em;overflow:auto;}
"""


def _write_json(data: Dict[str, Any], out: Path) -> None:
    if orjson:
        out.write_bytes(orjson.dumps(data))
    else:  # pragma: no cover - json fallback
        out.write_text(json.dumps(data, indent=2))


def _write_html(data: Dict[str, Any], out: Path) -> None:
    body = ["<html><head><meta charset='utf-8'><style>", MINIMAL_CSS, "</style></head><body>"]
    def section(title: str, content: Any) -> None:
        body.append(f"<h1>{title}</h1><section><pre>")
        body.append(json.dumps(content, indent=2))
        body.append("</pre></section>")

    section("Overview", data.get("overview", {}))
    if findings := data.get("findings"):
        section("Findings", findings)
    if signals := data.get("signals"):
        section("Signals", signals)
    if waf := data.get("waf_timeline"):
        section("WAF timeline", waf)
    if clusters := data.get("endpoint_clusters"):
        section("Endpoint Clusters", clusters)
    if params := data.get("param_inference"):
        section("Param Inference", params)
    if replay := data.get("replay_hits"):
        section("Replay Assist hits", replay)
    if diff := data.get("ci_diff"):
        section("CI Diff summary", diff)
    body.append("</body></html>")
    out.write_text("".join(body))


def compose(data: Dict[str, Any], outdir: str, fmt: str = "all") -> Dict[str, str]:
    """Compose JSON and/or HTML reports.

    Parameters
    ----------
    data:
        Report data structure.
    outdir:
        Directory to write to; created if missing.
    fmt:
        ``json``, ``html`` or ``all``.
    Returns
    -------
    Mapping of format to file path for generated reports.
    """
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    if fmt in ("json", "all"):
        json_path = out / "report.json"
        _write_json(data, json_path)
        paths["json"] = str(json_path)
    if fmt in ("html", "all"):
        html_path = out / "report.html"
        _write_html(data, html_path)
        paths["html"] = str(html_path)
    return paths
