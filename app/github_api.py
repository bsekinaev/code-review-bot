import base64
import httpx
from app.github_auth import get_installation_token

async def github_request(installation_id:int, method: str, endpoint:str, **kwargs):
    token = await get_installation_token(installation_id)
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json',
    }
    url = f'https://api.github.com{endpoint}'
    async with httpx.AsyncClient() as client:
        if method == 'GET':
            response = await client.get(url, headers=headers, **kwargs)
        elif method == 'POST':
            response = await client.post(url, headers=headers, **kwargs)
        else:
            raise ValueError(f'Method {method} not supported')
        response.raise_for_status()
        return response.json()

async def get_pull_request_files(installation_id:int, repo_full_name:str, pr_number:int):
    endpoint = f'/repos/{repo_full_name}/pulls/{pr_number}/files'
    return await github_request(installation_id, "GET", endpoint)

async def get_file_content(installation_id:int, repo_full_name:str, file_path:str, ref:str = None):
    endpoint = f'/repos/{repo_full_name}/contents/{file_path}'
    params = {}
    if ref:
        params['ref'] = ref
    data = await github_request(installation_id, "GET", endpoint, params=params)
    if data.get("content"):
        return base64.b64decode(data.get("content")).decode("utf-8")
    return ""

async def create_pull_request_review(installation_id:int, repo_full_name:str, pr_number:int, body:str, event: str = "COMMENT"):
    endpoint = f'/repos/{repo_full_name}/pulls/{pr_number}/reviews'
    data = {
        'body': body,
        'event': event,
    }
    return await github_request(installation_id, "POST", endpoint, json=data)