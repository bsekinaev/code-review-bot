import time, threading, jwt, httpx
from decouple import config

_token_cache: dict = {"token": None, "expires_at": 0}
_lock = threading.Lock()


def _load_config():
    app_id = config('GITHUB_APP_ID')
    key_path = config('GITHUB_PRIVATE_KEY_PATH')
    if not app_id or not key_path:
        raise RuntimeError("GITHUB_APP_ID и GITHUB_PRIVATE_KEY_PATH обязательны")
    with open(key_path, 'r') as f:
        return app_id, f.read()


def generate_jwt() -> str:
    app_id, private_key = _load_config()
    now = int(time.time())
    return jwt.encode({"iat": now - 60, "exp": now + 600, "iss": app_id}, private_key, algorithm='RS256')


async def get_installation_token(installation_id: int) -> str:
    now = time.time()
    with _lock:
        if _token_cache["token"] and now < _token_cache["expires_at"]:
            return _token_cache["token"]

    jwt_token = generate_jwt()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f'https://api.github.com/app/installations/{installation_id}/access_tokens',
            headers={"Authorization": f"Bearer {jwt_token}", "Accept": "application/vnd.github.v3+json"}
        )
        resp.raise_for_status()
        data = resp.json()
        with _lock:
            _token_cache["token"] = data["token"]
            _token_cache["expires_at"] = now + 3300  # 55 мин (токен живёт 60)
        return data["token"]