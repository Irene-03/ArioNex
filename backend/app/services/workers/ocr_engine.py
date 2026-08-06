"""
/// <summary>
/// OCR engine abstraction layer for ArioNex (ArioNex OCR Engine Abstraction)
/// </summary>
/// <remarks>
/// This module provides a pluggable client for the baidu/Unlimited-OCR model
/// (a multilingual, structure-aware 3B vision-language OCR model) hosted behind
/// an OpenAI-compatible vLLM or SGLang server.
///
/// Responsibilities:
///   1. Base64-encode a local image and call the server's /v1/chat/completions
///   2. Decode the structured output (Markdown with <|det|> markers)
///   3. Provide a guarded entry point that returns "" on failure/disable so the
///      caller (PaddleOCR) can act as a graceful fallback.
///
/// The feature is disabled until `services.unlimited_ocr.enabled` is set to
/// true in config.yaml and an OCR server is reachable at `base_url`.
/// </remarks>
"""

import base64
import logging
import os
import re
from typing import List

import requests

from app.core.config import settings

logger = logging.getLogger("arionex.ocr_engine")

# Matches the official model's block markers, e.g.:
#   <|det|>paragraph [0.0, 0.0, 1.0, 1.0]<|/det|>some text...
# Category "image" blocks are dropped (they contain no text to index).
DET_RE = re.compile(r"<\|det\|>([^<\s]+)(?:\s*\[[^\]]*\])?\s*<\|/det\|>(.*)", re.DOTALL)

_engine_instance = None


def _remove_det_markers(raw: str) -> str:
    """
    /// <summary>
    /// Strip <|det|>category [bbox] markers and group lines into blocks
    /// </summary>
    /// <param name="raw">Raw model output containing structural markers</param>
    /// <returns>Clean, block-structured plain text</returns>
    /// <remarks>
    /// Lines belonging to the same detected block are joined with newlines;
    /// different blocks are separated with a blank line.
    /// </remarks>
    """
    if not raw:
        return ""

    blocks: List[List[str]] = []
    current: List[str] = []

    for line in raw.splitlines():
        line = line.rstrip()
        if not line:
            continue

        match = DET_RE.match(line)
        if match:
            category = match.group(1).strip()
            content = match.group(2).strip()
            if category == "image":
                continue
            if current:
                blocks.append(current)
            current = [content] if content else []
            continue

        current.append(line)

    if current:
        blocks.append(current)

    return "\n\n".join("\n".join(block) for block in blocks).strip()


class UnlimitedOCREngine:
    """
    /// <summary>
    /// HTTP client for a vLLM/SGLang-hosted baidu/Unlimited-OCR server
    /// </summary>
    /// <remarks>
    /// Talks to the OpenAI-compatible chat completions endpoint. The vLLM
    /// official image (vllm/vllm-openai:unlimited-ocr) handles the custom
    /// no-repeat n-gram logit processor automatically, so a plain JSON request
    /// with an `images_config` block is all that is needed.
    /// </remarks>
    """

    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.endpoint = f"{self.base_url}/v1/chat/completions"
        # OCR of long documents can legitimately take minutes
        self.timeout = 600

    def _encode_image(self, image_path: str) -> dict:
        """
        /// <summary>
        /// Encode a local image file as a data-URL ready for the model API
        /// </summary>
        """
        ext = os.path.splitext(image_path)[1].lower()
        if ext in (".jpg", ".jpeg"):
            mime = "image/jpeg"
        elif ext in (".png", ".webp", ".bmp", ".tiff", ".gif"):
            mime = f"image/{ext.lstrip('.')}"
        else:
            mime = "image/png"

        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")

        return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}

    def extract_text(self, image_path: str, prompt: str = "document parsing.",
                     image_mode: str = "base") -> str:
        """
        /// <summary>
        /// Send one image to the OCR server and return clean extracted text
        /// </summary>
        /// <param name="image_path">Local path of the image to parse</param>
        /// <param name="prompt">Instruction prompt for the model</param>
        /// <param name="image_mode">"gundam" for single images, "base" for multi-page/PDF</param>
        /// <returns>Extracted, block-structured text (may be empty)</returns>
        """
        content = [
            {"type": "text", "text": prompt},
            self._encode_image(image_path),
        ]
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "images_config": {"image_mode": image_mode},
        }

        response = requests.post(self.endpoint, json=payload, timeout=self.timeout)
        response.raise_for_status()

        raw = response.json()["choices"][0]["message"]["content"]
        return _remove_det_markers(raw)


def _get_unlimited_engine() -> UnlimitedOCREngine:
    """Return the lazily-created, single shared engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = UnlimitedOCREngine(
            base_url=settings.unlimited_ocr_base_url,
            model_name=settings.unlimited_ocr_model,
        )
    return _engine_instance


def ocr_image_via_unlimited(image_path: str, multi_page: bool = False) -> str:
    """
    /// <summary>
    /// Guarded entry point: OCR a single image via the Unlimited-OCR server
    /// </summary>
    /// <param name="image_path">Local path of the image to parse</param>
    /// <param name="multi_page">Use "base" mode (single-image safe default)</param>
    /// <returns>Extracted text, or an empty string on disable/error</returns>
    /// <remarks>
    /// Never raises: failures are logged and the caller should fall back to
    /// the local PaddleOCR engine.
    /// </remarks>
    """
    if not settings.services.unlimited_ocr:
        return ""

    image_mode = "base" if multi_page else settings.unlimited_ocr_image_mode
    try:
        text = _get_unlimited_engine().extract_text(image_path, image_mode=image_mode)
        logger.info(
            f"Unlimited-OCR extracted {len(text)} character(s) from '{image_path}' (mode={image_mode})"
        )
        return text
    except Exception as e:
        logger.warning(f"Unlimited-OCR request failed ({str(e)}); falling back to PaddleOCR")
        return ""
