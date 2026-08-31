from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class PronunciationDownloadError(RuntimeError):
    """Raised when the pronunciation audio cannot be downloaded safely."""


def build_pronunciation_url(
    api_url: str,
    word: str,
    language: str = "de",
) -> str:
    """Build the configured TTS URL without performing any network access."""
    base_url = api_url.strip()
    if not base_url:
        raise ValueError("The pronunciation API URL is empty.")

    params = urlencode(
        {
            "ie": "UTF-8",
            "client": "tw-ob",
            "tl": language.strip() or "de",
            "q": word.strip()[:180],
        }
    )
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{params}"


def download_pronunciation(
    url: str,
    timeout_seconds: float,
    max_bytes: int = 5_000_000,
) -> bytes:
    """Download pronunciation audio with Python's HTTPS stack.

    Using Python's standard-library HTTPS client avoids dependence on Qt's
    runtime TLS plugin. Certificate verification remains enabled.
    """
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) DeutschDictionary/2.1",
            "Accept": "audio/mpeg,audio/*;q=0.9,*/*;q=0.1",
            "Connection": "close",
        },
    )

    try:
        with urlopen(request, timeout=max(1.0, float(timeout_seconds))) as response:
            status = getattr(response, "status", 200)
            if status and int(status) >= 400:
                raise PronunciationDownloadError(
                    f"The pronunciation service returned HTTP {status}."
                )

            content_type = ""
            headers = getattr(response, "headers", None)
            if headers is not None:
                try:
                    content_type = headers.get_content_type().lower()
                except (AttributeError, TypeError, ValueError):
                    content_type = str(headers.get("Content-Type", "")).split(";", 1)[0].lower()

            audio = response.read(max_bytes + 1)
    except HTTPError as exc:
        raise PronunciationDownloadError(
            f"The pronunciation service returned HTTP {exc.code}."
        ) from exc
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise PronunciationDownloadError(f"HTTPS request failed: {reason}") from exc
    except TimeoutError as exc:
        raise PronunciationDownloadError("The pronunciation request timed out.") from exc
    except OSError as exc:
        raise PronunciationDownloadError(f"Network error: {exc}") from exc

    if len(audio) > max_bytes:
        raise PronunciationDownloadError("The pronunciation response was unexpectedly large.")
    if len(audio) < 100:
        raise PronunciationDownloadError("The pronunciation service returned no audio.")

    # A failed web service can return an HTML error page with HTTP 200.
    prefix = audio[:256].lstrip().lower()
    if content_type and not content_type.startswith("audio/"):
        if prefix.startswith((b"<!doctype html", b"<html", b"{")):
            raise PronunciationDownloadError(
                f"The pronunciation service returned {content_type}, not audio."
            )

    return audio
