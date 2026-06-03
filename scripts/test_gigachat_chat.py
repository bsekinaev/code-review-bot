import pytest
import base64
import httpx
from decouple import config

pytestmark = pytest.mark.asyncio

CLIENT_ID = config("GIGACHAT_CLIENT_ID", default="")
CLIENT_SECRET = config("GIGACHAT_CLIENT_SECRET", default="")


@pytest.mark.skipif(not CLIENT_ID or not CLIENT_SECRET, reason="GigaChat credentials not set")
async def test_gigachat_token():
    """Интеграционный тест: получение токена."""
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth = base64.b64encode(credentials.encode()).decode()

    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.post(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "RqUID": "test-uuid-123",
                "Authorization": f"Basic {auth}",
            },
            data={"scope": "GIGACHAT_API_PERS"},
            timeout=30,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data.get("expires_in", 0) > 0


@pytest.mark.skipif(not CLIENT_ID or not CLIENT_SECRET, reason="GigaChat credentials not set")
async def test_gigachat_chat():
    """Интеграционный тест: запрос к Chat API."""
    # Сначала получаем токен (код дублируется для простоты)
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth = base64.b64encode(credentials.encode()).decode()

    async with httpx.AsyncClient(verify=False) as client:
        # Получение токена
        token_resp = await client.post(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "RqUID": "test-uuid-456",
                "Authorization": f"Basic {auth}",
            },
            data={"scope": "GIGACHAT_API_PERS"},
            timeout=30,
        )
        token = token_resp.json()["access_token"]

        # Запрос к Chat API
        chat_resp = await client.post(
            "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json={
                "model": "GigaChat",
                "messages": [{"role": "user", "content": "Привет, напиши 'тест'"}],
                "temperature": 0.2,
            },
            timeout=60,
        )
        assert chat_resp.status_code == 200, f"Expected 200, got {chat_resp.status_code}: {chat_resp.text}"
        data = chat_resp.json()
        assert "choices" in data
        assert len(data["choices"]) > 0