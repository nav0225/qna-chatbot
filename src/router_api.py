import os
import time
import random
import requests
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Supported models (add/remove as availability changes)
OPENROUTER_MODELS = [
    {"id": "openrouter/auto", "name": "OpenRouter Auto", "description": "Smart router (auto-pick)"},
    {"id": "mistralai/mistral-7b-instruct:free", "name": "Mistral-7B-Instruct", "description": "Fast, instruct-tuned"},
    {"id": "deepseek-ai/deepseek-chat:free", "name": "DeepSeek Chat", "description": "Open-source conversational"},
    {"id": "meta-llama/llama-2-7b-chat:free", "name": "Llama-2-7B-Chat", "description": "Meta's conversational Llama"},
    {"id": "meta-llama/llama-3-8b-instruct:free", "name": "Llama-3-8B-Instruct", "description": "Latest Meta Llama, instruct"},
    # Add more models as desired
]


class ChatRouter:
    def __init__(self, api_key: Optional[str] = None, base_url: str = BASE_URL):
        self.api_key = api_key or OPENROUTER_API_KEY
        self.base_url = base_url

        if not self.api_key:
            raise RuntimeError("❌ OPENROUTER_API_KEY not found. Set it in .env or environment variables.")

    @staticmethod
    def list_models() -> List[Dict[str, str]]:
        """Return supported model metadata."""
        return OPENROUTER_MODELS

    @staticmethod
    def get_model_by_id(model_id: str) -> Optional[Dict[str, str]]:
        """Get a model definition by its ID."""
        return next((m for m in OPENROUTER_MODELS if m["id"] == model_id), None)

    def send_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.8,
        top_p: float = 0.95,
        retries: int = 3,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Send a chat completion request to OpenRouter.
        
        Returns:
            (answer, metadata) tuple
            - answer: str
            - metadata: dict (raw API response, usage info, model)
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }

        if DEBUG:
            print(">>> Payload:", payload)

        for attempt in range(retries):
            try:
                resp = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
                resp.raise_for_status()
                data = resp.json()

                if DEBUG:
                    print(">>> Response JSON:", data)

                if "choices" in data and data["choices"]:
                    answer = data["choices"][0]["message"]["content"].strip()
                    metadata = {
                        "model": data.get("model", model),
                        "usage": data.get("usage", {}),
                        "raw": data,
                    }
                    return answer, metadata

                if "error" in data:
                    return f"[API ERROR]: {data['error'].get('message', 'Unknown error')}", {"raw": data}

                return "[ERROR]: Unexpected API response", {"raw": data}

            except requests.exceptions.Timeout:
                return "[ERROR]: Request timed out. Try again later.", {}
            except requests.exceptions.ConnectionError:
                return "[ERROR]: Connection error. Check your internet.", {}
            except requests.exceptions.HTTPError as e:
                if resp.status_code == 429 and attempt < retries - 1:
                    wait = (2 ** attempt) + random.random()
                    if DEBUG:
                        print(f"[WARN] Rate limited. Retrying in {wait:.2f}s...")
                    time.sleep(wait)
                    continue
                return f"[HTTP ERROR {resp.status_code}]: {resp.text}", {}
            except Exception as exc:
                return f"[ERROR]: {str(exc)}", {}

        return "[ERROR]: Max retries exceeded.", {}
