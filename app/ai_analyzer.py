import base64
import json
import logging
import re
import time
from typing import Optional

import httpx
from decouple import config
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger("uvicorn")

# === Конфигурация из .env ===
AI_ENABLED = config("AI_ENABLED", default=False, cast=bool)
GIGACHAT_CLIENT_ID = config("GIGACHAT_CLIENT_ID", default="")
GIGACHAT_CLIENT_SECRET = config("GIGACHAT_CLIENT_SECRET", default="")
GIGACHAT_SCOPE = config("GIGACHAT_SCOPE", default="GIGACHAT_API_PERS")

# === Эндпоинты ===
TOKEN_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_BASE = "https://gigachat.devices.sberbank.ru/api/v1"


# === Кэш токена ===
class TokenCache:
    """Кэширует Access token с учётом времени жизни (30 минут)."""
    _token: Optional[str] = None
    _expires_at: float = 0

    @classmethod
    def get(cls) -> Optional[str]:
        if cls._token and time.time() < cls._expires_at:
            return cls._token
        return None

    @classmethod
    def set(cls, token: str, expires_in: int = 1800):
        cls._token = token
        cls._expires_at = time.time() + expires_in - 60  # -60 сек буфер

    @classmethod
    def clear(cls):
        cls._token = None
        cls._expires_at = 0


SYSTEM_PROMPT = """
Ты Senior Python-разработчик и эксперт по безопасности.
Проанализируй предоставленный код и изменения (diff).
Верни ТОЛЬКО валидный JSON. Без markdown-обёрток, без комментариев.

Формат:
{
  "security_issues": [{"line": int, "severity": "high|medium|low", "description": str}],
  "code_smells": [{"line": int, "type": str, "suggestion": str}],
  "refactoring_tip": str или null,
  "test_idea": str или null
}
Фокусируйся ТОЛЬКО на изменённых строках. Если проблем нет — верни пустые списки.
"""


def _clean_json(raw: str) -> str:
    """Убирает markdown-обёртки, которые LLM иногда добавляет."""
    return re.sub(r"```(?:json)?\n?|\n?```", "", raw).strip()


def _get_auth_header() -> str:
    """Генерирует Basic Auth header из Client ID + Secret."""
    credentials = f"{GIGACHAT_CLIENT_ID}:{GIGACHAT_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception)
)
async def _get_access_token() -> str:
    """Получает Access token через OAuth2-флоу (согласно докам)."""
    cached = TokenCache.get()
    if cached:
        return cached

    async with httpx.AsyncClient(verify=False) as client:  # verify=False для Windows/dev
        response = await client.post(
            TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "RqUID": "f809081b-e1f7-42a2-9bd7-8c00feaff042",  # можно генерировать UUID
                "Authorization": _get_auth_header(),
            },
            data={"scope": GIGACHAT_SCOPE},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        token = data["access_token"]
        expires_in = data.get("expires_in", 1800)
        TokenCache.set(token, expires_in)
        return token


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception)
)
async def analyze_with_ai(file_content: str, filename: str, patch: str) -> dict:
    if not AI_ENABLED or not GIGACHAT_CLIENT_ID or not GIGACHAT_CLIENT_SECRET or not patch:
        return {}

    prompt = f"Файл: {filename}\n\nКод:\n```python\n{file_content}\n```\n\nИзменения:\n```\n{patch}\n```"
    token = await _get_access_token()

    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{API_BASE}/chat/completions",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json={
                    "model": "GigaChat",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 600,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            raw = data["choices"][0]["message"]["content"]
            return json.loads(_clean_json(raw))

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            TokenCache.clear()  # Токен протух — очистим кэш
        logger.warning(f"⚠️ GigaChat HTTP error: {e}")
        return {}
    except Exception as e:
        logger.warning(f"⚠️ GigaChat analysis failed for {filename}: {e}")
        return {}