from __future__ import annotations

import unittest
from email.message import Message
from unittest.mock import patch
from urllib.error import URLError

from pronunciation_core import (
    PronunciationDownloadError,
    build_pronunciation_url,
    download_pronunciation,
)


class FakeResponse:
    def __init__(self, data: bytes, content_type: str = "audio/mpeg", status: int = 200):
        self._data = data
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, amount: int = -1) -> bytes:
        return self._data if amount < 0 else self._data[:amount]


class PronunciationCoreTests(unittest.TestCase):
    def test_build_url_encodes_umlaut(self) -> None:
        url = build_pronunciation_url(
            "https://translate.google.com/translate_tts", "müssen", "de"
        )
        self.assertIn("tl=de", url)
        self.assertIn("q=m%C3%BCssen", url)
        self.assertIn("client=tw-ob", url)

    def test_existing_query_string_uses_ampersand(self) -> None:
        url = build_pronunciation_url("https://example.test/tts?voice=1", "gehen")
        self.assertIn("?voice=1&ie=UTF-8", url)

    @patch("pronunciation_core.urlopen")
    def test_download_returns_audio(self, mocked_urlopen) -> None:
        expected = b"ID3" + b"x" * 500
        mocked_urlopen.return_value = FakeResponse(expected)
        self.assertEqual(download_pronunciation("https://example.test", 2), expected)

    @patch("pronunciation_core.urlopen")
    def test_html_response_is_rejected(self, mocked_urlopen) -> None:
        mocked_urlopen.return_value = FakeResponse(
            b"<!doctype html>" + b"x" * 500, "text/html"
        )
        with self.assertRaises(PronunciationDownloadError):
            download_pronunciation("https://example.test", 2)

    @patch("pronunciation_core.urlopen", side_effect=URLError("TLS failed"))
    def test_network_error_is_readable(self, mocked_urlopen) -> None:
        with self.assertRaisesRegex(PronunciationDownloadError, "TLS failed"):
            download_pronunciation("https://example.test", 2)


if __name__ == "__main__":
    unittest.main()
