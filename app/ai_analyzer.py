import json
import logging
import re
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from decouple import config

logger = logging.getLogger("uvicorn")

AI_ENABLED = config("AI_ENABLED", default=False, cast=bool)
AI_MODEL = config("AI_MODEL", default="gpt-4o-mini")
client = AsyncOpenAI(api_key=config("OPENAI_API_KEY", default=""))

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

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception)
)
async def analyze_with_ai(file_content: str, filename: str, patch: str) -> dict:
    if not AI_ENABLED or not client.api_key or not patch:
        return {}

    prompt = f"Файл: {filename}\n\nКод:\n```python\n{file_content}\n```\n\nИзменения:\n```\n{patch}\n```"

    try:
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=600,
            temperature=0.2,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(_clean_json(raw))
    except Exception as e:
        logger.warning(f"⚠️ AI analysis failed for {filename}: {e}")
        return {}