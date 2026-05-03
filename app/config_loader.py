import yaml
import base64
import logging
from app.github_api import github_request

logger = logging.getLogger('uvicorn')

DEFAULT_CONFIG = {
    'ignore': [],
    'select': [],
    'exclude': [],
}

async def get_review_config(installation_id : int, repo_full_name: str, head_sha: str) -> dict:
    try:
        endpoint = f'/repos/{repo_full_name}/contents/.codereview.yml?ref={head_sha}'
        data = await github_request(installation_id, "GET", endpoint)
        content =  data.get("content")
        if not content:
            return DEFAULT_CONFIG

        yaml_text = base64.b64decode(content).decode("utf-8")
        config = yaml.safe_load(yaml_text) or {}

        return {
            'ignore': config.get('ignore', []),
            'select': config.get('select', []),
            'exclude': config.get('exclude', []),
        }
    except Exception as e:
        logger.error(f'Файл .codereview.yml не найден или ошибка парсинга{e}')
        return DEFAULT_CONFIG
