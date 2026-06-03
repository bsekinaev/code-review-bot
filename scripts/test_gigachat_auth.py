import asyncio
import base64
import httpx
import uuid
from decouple import config

CLIENT_ID = config("GIGACHAT_CLIENT_ID", default="")
CLIENT_SECRET = config("GIGACHAT_CLIENT_SECRET", default="")
SCOPE = config("GIGACHAT_SCOPE", default="GIGACHAT_API_PERS")


async def debug_token():
    print(f"🔍 CLIENT_ID: {CLIENT_ID[:10] if CLIENT_ID else 'NOT SET'}...")
    print(f"🔍 CLIENT_SECRET: {'*' * 10 if CLIENT_SECRET else 'NOT SET'}")
    print(f"🔍 SCOPE: {SCOPE}")

    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ Креденшелы не заданы в .env")
        return

    # Генерируем Basic Auth
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(credentials.encode()).decode().strip()
    print(f"🔍 Authorization header starts with: Basic {auth_b64[:20]}...")

    async with httpx.AsyncClient(verify=False) as client:
        try:
            resp = await client.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "RqUID": str(uuid.uuid4()),  # ✅ Валидный UUID
                    "Authorization": f"Basic {auth_b64}",
                },
                data={"scope": SCOPE},  # ✅ httpx сам закодирует как form-data
                timeout=30,
            )
            print(f"\n📡 Response status: {resp.status_code}")
            print(f"📡 Response headers: {dict(resp.headers)}")
            print(f"📡 Response body: {resp.text[:500]}")  # Первые 500 символов

            if resp.status_code == 200:
                data = resp.json()
                print(f"\n✅ Token: {data['access_token'][:30]}...")
                print(f"✅ Expires in: {data.get('expires_in')} sec")
            else:
                print(f"\n❌ Ошибка {resp.status_code}: {resp.text}")

        except httpx.RequestError as e:
            print(f"\n❌ Network error: {e}")
        except Exception as e:
            print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")


asyncio.run(debug_token())