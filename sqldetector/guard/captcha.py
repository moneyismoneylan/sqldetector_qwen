"""Captcha detection utilities."""

from __future__ import annotations

CAPTCHA_MARKERS = {"captcha", "g-recaptcha", "hcaptcha"}


def is_captcha(html: str) -> bool:
    lower = html.lower()
    return any(m in lower for m in CAPTCHA_MARKERS)


def notify(narrator, lang: str = "tr") -> None:
    msg = "Captcha: manuel doğrulama gerekli" if lang == "tr" else "Captcha: manual verification required"
    if narrator:
        narrator.note(msg)


__all__ = ["is_captcha", "notify", "CAPTCHA_MARKERS"]
