import httpx
from typing import Optional


class GitHubClient:
    _instance: Optional[httpx.AsyncClient] = None

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """Возвращает singleton-экземпляр клиента."""
        if cls._instance is None:
            cls._instance = httpx.AsyncClient(
                base_url="https://api.github.com",
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "CodeReviewBot/1.0"
                },
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=50,
                    keepalive_expiry=60.0
                ),
                follow_redirects=True
            )
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        """Закрывает клиент при остановке приложения."""
        if cls._instance:
            await cls._instance.aclose()
            cls._instance = None