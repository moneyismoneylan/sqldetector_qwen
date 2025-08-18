"""Hybrid SAST to DAST seeding utilities.

These helpers scan source code or JavaScript snippets to derive
potential HTTP endpoints.  The goal is to narrow dynamic scans to a
relevant set of URLs discovered statically.
"""
from __future__ import annotations

from dataclasses import dataclass
import ast
import re
from typing import List, Set


@dataclass(frozen=True)
class Endpoint:
    """Representation of an HTTP endpoint."""

    method: str
    path: str


def extract_endpoints_from_code(code: str) -> List[Endpoint]:
    """Very small static analysis extracting HTTP calls.

    The implementation purposefully keeps the logic compact and
    dependency free.  It looks for calls like ``client.get("/foo")``
    and returns the HTTP method and path.
    """

    endpoints: Set[Endpoint] = set()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802 - visitor API
            if isinstance(node.func, ast.Attribute):
                method = node.func.attr.lower()
                if method in {"get", "post", "put", "delete"}:
                    if node.args and isinstance(node.args[0], ast.Constant):
                        path = node.args[0].value
                        endpoints.add(Endpoint(method.upper(), str(path)))
            self.generic_visit(node)

    Visitor().visit(tree)
    return sorted(endpoints, key=lambda e: (e.method, e.path))


def extract_endpoints_from_js(js: str) -> List[str]:
    """Extract fetch/XHR URLs from JavaScript snippets."""

    pattern = re.compile(r"fetch\(['\"](.*?)['\"]")
    return sorted(set(pattern.findall(js)))
