"""HTML boilerplate stripping for cleaner diffs."""

from __future__ import annotations

import re
from typing import Tuple

_skeleton_re = re.compile(r">[^<]+<")
_text_re = re.compile(r"<[^>]+>")


def strip_boilerplate(html: str) -> str:
    return _skeleton_re.sub("><", html)


def _dynamic_text(html: str) -> str:
    return _text_re.sub("", html)


def diff_dynamic(old: str, new: str) -> Tuple[str, str]:
    return _dynamic_text(old), _dynamic_text(new)


__all__ = ["strip_boilerplate", "diff_dynamic"]
