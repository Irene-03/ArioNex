"""
/// <summary>
/// ArioNex Unlimited-OCR verification script (ArioNex Unlimited-OCR Test Suite)
/// </summary>
/// <remarks>
/// Unit tests for the pluggable Open-Source OCR engine (baidu/Unlimited-OCR).
/// These tests are CPU-friendly and do NOT require a GPU or a live vLLM/SGLang
/// server: they validate the marker post-processing, the guarded entry point,
/// and the image MIME encoding.
/// </remarks>
"""

import sys
import os
import tempfile

# Add the project path so the app package can be detected
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from unittest import mock

from app.core.config import settings
from app.services.workers.ocr_engine import (
    _remove_det_markers,
    UnlimitedOCREngine,
    ocr_image_via_unlimited,
)


def _make_temp_image(suffix: str = ".png") -> str:
    """Create a throwaway image file and return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\nfakedata")
    return path


def test_det_marker_post_processing():
    """
    <summary>
    Validate that structural <|det|> markers are stripped and blocks are grouped
    </summary>
    """
    print("Testing <|det|> marker post-processing...")

    sample = (
        "<|det|>title [0.1,0.1,0.9,0.2]<|/det|>ACME Invoice\n"
        "<|det|>text [0.1,0.2,0.9,0.3]<|/det|>Invoice #1234\n"
        "<|det|>image [0.1,0.3,0.9,0.5]<|/det|>\n"
        "<|det|>paragraph [0.1,0.5,0.9,0.8]<|/det|>Thank you for your purchase."
    )
    cleaned = _remove_det_markers(sample)
    assert "Invoice #1234" in cleaned, "Block content must survive marker stripping"
    assert "image" not in cleaned, "image category must be dropped"
    assert "ACME Invoice" in cleaned, "first block must be preserved"
    assert "\n\n" in cleaned, "distinct blocks must be separated by a blank line"
    assert "<|det|>" not in cleaned, "markers must be fully removed"

    assert _remove_det_markers("") == "", "empty input must yield empty output"
    print(" Clean marker post-processing PASSED.\n")


def test_guarded_entry_disabled_by_default():
    """
    <summary>
    When the feature is disabled, the entry point must return "" without any
    network call, so PaddleOCR remains the active engine.
    </summary>
    """
    print("Testing disabled default (no network) behavior...")

    original = settings.services.unlimited_ocr
    try:
        settings.services.unlimited_ocr = False
        with mock.patch("app.services.workers.ocr_engine.requests.post") as mock_post:
            result = ocr_image_via_unlimited("nonexistent.png")
            assert result == "", "disabled engine must return an empty string"
            mock_post.assert_not_called(), "no HTTP call may be made when disabled"
    finally:
        settings.services.unlimited_ocr = original

    print("PASS: disabled engine short-circuits with no network call.\n")


def test_guarded_error_return():
    """
    <summary>
    When enabled but the server errors, the entry point must swallow the error
    and return "" so the caller can fall back to PaddleOCR.
    </summary>
    """
    print("Testing graceful error fallback...")

    original_enabled = settings.services.unlimited_ocr
    original_base = settings.unlimited_ocr_base_url
    original_model = settings.unlimited_ocr_model

    try:
        settings.services.unlimited_ocr = True
        settings.unlimited_ocr_base_url = "http://127.0.0.1:1"
        settings.unlimited_ocr_model = "baidu/Unlimited-OCR"

        image_path = _make_temp_image()
        try:
            result = ocr_image_via_unlimited(image_path)
            assert result == "", "an errored request must yield an empty string, never raise"
        finally:
            os.unlink(image_path)
    finally:
        settings.services.unlimited_ocr = original_enabled
        settings.unlimited_ocr_base_url = original_base
        settings.unlimited_ocr_model = original_model

    print("PASS error fallback returns empty string.\n")


def test_image_mime_encoding():
    """
    <summary>
    Validate MIME types produced when base64-encoding images for the API
    </summary>
    """
    print("Testing image MIME encoding...")

    engine = UnlimitedOCREngine(base_url="http://localhost:8000", model_name="baidu/Unlimited-OCR")
    assert engine.endpoint == "http://localhost:8000/v1/chat/completions", "endpoint must match"

    jpg_mock = mock.mock_open(read_data=b"\xff\xd8\xff\xe0")
    with mock.patch("builtins.open", jpg_mock):
        part = engine._encode_image("photo.jpg")
        assert part["image_url"]["url"].startswith("data:image/jpeg;base64,"), "jpeg mime expected"

    png_mock = mock.mock_open(read_data=b"\x89PNG\r\n\x1a\n")
    with mock.patch("builtins.open", png_mock):
        part = engine._encode_image("invoice.png")
        assert part["image_url"]["url"].startswith("data:image/png;base64,"), "png mime expected"

    print("PASS MIME encoding builds correct data-URLs.\n")


def test_ocr_engine_http_request():
    """
    <summary>
    Validate the full protected path: payload shape and marker post-processing
    of a mocked server response.
    </summary>
    """
    print("Testing HTTP request build + response parsing (mocked)...")

    original_enabled = settings.services.unlimited_ocr
    original_base = settings.unlimited_ocr_base_url
    original_model = settings.unlimited_ocr_model
    original_mode = settings.unlimited_ocr_image_mode

    fake_response = mock.MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "choices": [{"message": {"content": "<|det|>text [0,0,1,1]<|/det|>Hello world"}}]
    }

    try:
        settings.services.unlimited_ocr = True
        settings.unlimited_ocr_base_url = "http://127.0.0.1:9999"
        settings.unlimited_ocr_model = "baidu/Unlimited-OCR"
        settings.unlimited_ocr_image_mode = "gundam"

        with mock.patch("app.services.workers.ocr_engine.requests.post", return_value=fake_response) as mock_post:
            image_path = _make_temp_image()
            try:
                text = ocr_image_via_unlimited(image_path)
            finally:
                os.unlink(image_path)
            assert text == "Hello world", "mocked content must be cleaned and returned"

            _, kwargs = mock_post.call_args
            payload = kwargs["json"]
            assert payload["messages"][0]["content"][0]["text"] == "document parsing."
            assert payload["messages"][0]["content"][1]["type"] == "image_url"
            assert payload["images_config"]["image_mode"] == "gundam"
            assert payload["temperature"] == 0
    finally:
        settings.services.unlimited_ocr = original_enabled
        settings.unlimited_ocr_base_url = original_base
        settings.unlimited_ocr_model = original_model
        settings.unlimited_ocr_image_mode = original_mode

    print("PASS mocked request/response passed.\n")


def test_config_has_unlimited_ocr():
    """Validate that the config.yaml toggle is present and disabled by default."""
    print("Testing config wiring...")
    assert hasattr(settings.services, "unlimited_ocr"), "services.unlimited_ocr toggle must exist"
    assert settings.services.unlimited_ocr is False, "unlimited_ocr must default to False in config.yaml"
    print("PASS config toggle present and disabled.\n")


if __name__ == "__main__":
    print("=========================================")
    print("STARTING UNLIMITED-OCR TEST SUITE")
    print("=========================================")
    try:
        test_config_has_unlimited_ocr()
        test_det_marker_post_processing()
        test_guarded_entry_disabled_by_default()
        test_guarded_error_return()
        test_image_mime_encoding()
        test_ocr_engine_http_request()
        print("=========================================")
        print("ALL UNLIMITED-OCR TESTS COMPLETED SUCCESSFULLY!")
        print("=========================================")
        sys.exit(0)
    except AssertionError as e:
        print(f"FAILED: {str(e)}")
        sys.exit(1)