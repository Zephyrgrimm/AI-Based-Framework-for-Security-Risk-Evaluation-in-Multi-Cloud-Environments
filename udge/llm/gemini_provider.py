"""Google Gemini API Provider."""
import base64
import json
import urllib.request
from pathlib import Path
from udge.core.exceptions import LLMProviderError
from udge.llm.provider_base import BaseLLMProvider

class GeminiProvider(BaseLLMProvider):
    """Integrates with Google Gemini API."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System Instructions:\n{system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will strictly follow these instructions."}]})

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        data = json.dumps({"contents": contents}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            raise LLMProviderError(f"Gemini API request failed: {e}") from e

    def generate_vision(self, prompt: str, image_path: Path) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        b64_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        ext = image_path.suffix.lstrip(".").lower()
        mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"

        contents = [{
            "role": "user",
            "parts": [
                {"text": prompt or "Transcribe all text, numbers, and diagrams in this image with exact precision:"},
                {"inline_data": {"mime_type": mime, "data": b64_data}}
            ]
        }]

        data = json.dumps({"contents": contents}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            raise LLMProviderError(f"Gemini Vision API request failed: {e}") from e
