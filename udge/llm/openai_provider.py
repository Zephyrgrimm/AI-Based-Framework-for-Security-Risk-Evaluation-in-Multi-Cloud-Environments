"""OpenAI-compatible LLM Provider."""
import base64
import json
import urllib.request
from pathlib import Path
from udge.core.exceptions import LLMProviderError
from udge.llm.provider_base import BaseLLMProvider

class OpenAIProvider(BaseLLMProvider):
    """Integrates with OpenAI API or any OpenAI-compatible API (Ollama, Groq, etc.)."""

    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": 0.2
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise LLMProviderError(f"OpenAI API request failed: {e}") from e

    def generate_vision(self, prompt: str, image_path: Path) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        b64_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        ext = image_path.suffix.lstrip(".").lower()
        mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt or "Transcribe all text, numbers, and describe data in this image:"},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_data}"}}
            ]
        }]

        data = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": 0.1
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise LLMProviderError(f"OpenAI Vision API request failed: {e}") from e
