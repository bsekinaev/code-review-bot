import pytest
from unittest.mock import patch, AsyncMock
from app.telegram_bot import send_telegram_message

@pytest.mark.asyncio
async def test_send_message_success():
    fake_response = AsyncMock()
    fake_response.raise_for_status = lambda: None

    # Патчим и токены, и пост-запрос
    with patch('app.telegram_bot.BOT_TOKEN', 'dummy_token'), \
         patch('app.telegram_bot.CHAT_ID', 'dummy_chat'), \
         patch('app.telegram_bot.httpx.AsyncClient.post', new=AsyncMock(return_value=fake_response)) as mock_post:

        result = await send_telegram_message('Тест')
        assert result is True
        mock_post.assert_called_once()

@pytest.mark.asyncio
async def test_send_message_no_token():
    # Только токен отсутствует
    with patch('app.telegram_bot.BOT_TOKEN', None):
        result = await send_telegram_message('Тест')
        assert result is False