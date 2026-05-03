import time, jwt, httpx
from http.client import responses

from decouple import config

APP_ID = config('GITHUB_APP_ID')
PRIVATE_KEY_PATH = config('GITHUB_PRIVATE_KEY_PATH')

with open(f'{PRIVATE_KEY_PATH}', 'r') as f:
    PRIVATE_KEY = f.read()

def generate_jwt():
    now = int(time.time())
    payload = {
        'iat': now - 60,
        'exp': now + 600,
        'iss': APP_ID,
    }
    token = jwt.encode(payload, PRIVATE_KEY, algorithm='RS256')
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