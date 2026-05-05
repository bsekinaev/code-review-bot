import time, jwt, httpx
from functools import lru_cache
from decouple import config

def _load_config():
    """Ленивая загрузка настроек GitHub App."""
    app_id = config('GITHUB_APP_ID', default=None)
    key_path = config('GITHUB_PRIVATE_KEY_PATH', default=None)
    if not app_id or not key_path:
        raise RuntimeError("GITHUB_APP_ID и GITHUB_PRIVATE_KEY_PATH обязательны")
    with open(key_path, 'r') as f:
        private_key = f.read()
    return app_id, private_key

with open(f'{PRIVATE_KEY_PATH}', 'r') as f:
    PRIVATE_KEY = f.read()

def generate_jwt():
    app_id, private_key = _load_config()
    now = int(time.time())
    payload = {
        'iat': now - 60,
        'exp': now + 600,
        'iss': app_id,
    }
    token = jwt.encode(payload, private_key, algorithm='RS256')
    return token

async def get_installation_token(installation_id: int):
    jwt_token = generate_jwt()
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Accept': 'application/vnd.github.v3+json',
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(f'https://api.github.com/app/installations/{installation_id}/access_tokens',
                                    headers=headers,
                                    )
        response.raise_for_status()
        data = response.json()
        return data['token']