import pytest
import base64
from unittest.mock import patch, AsyncMock
from app.config_loader import get_review_config

@pytest.mark.asyncio
async def test_config_exists():
    yaml_content = """
    ignore:
      - F401
      - E501
    exclude:
      - "migrations/*"
    """
    encoded = base64.b64encode(yaml_content.encode('utf-8')).decode('utf-8')
    fake_response = {'content': encoded}

    with patch('app.config_loader.github_request', new=AsyncMock(return_value=fake_response)):
        config = await get_review_config(123,'user/repo','abc123')
        assert config['ignore'] == ['F401', 'E501']
        assert config['select'] == []
        assert config['exclude'] == ['migrations/*']

@pytest.mark.asyncio
async def test_config_missing():
    with patch('app.config_loader.github_request', new=AsyncMock(side_effect=Exception('404'))):
        config = await get_review_config(123,'user/repo','abc123')
        assert config['ignore'] == []
        assert config['select'] == []