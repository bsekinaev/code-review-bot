import httpx
import logging
from decouple import config

logger = logging.getLogger('uvicorn')

BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default=None)
CHAT_ID = config('TELEGRAM_CHAT_ID', default=None)

async def send_telegram_message(text: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("Telegram не настроен (токен или chat_id отсутствуют).")
        return False

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info("Уведомление отправлено в Telegram.")
            return True
    except Exception as e:
        logger.error(f'Ошибка отправки в Telegram: {e}')
        return False