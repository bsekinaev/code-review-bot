import asyncio
import hmac
import hashlib
import json
import logging
import fnmatch
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from decouple import config
from app.diff_parser import parse_diff_ranges
from app.github_api import get_pull_request_files, get_file_content, create_pull_request_review
from app.config_loader import get_review_config
from app.linter import run_ruff
from app.telegram_bot import send_telegram_message

WEBHOOK_SECRET = config("WEBHOOK_SECRET")
app = FastAPI()
logger = logging.getLogger('uvicorn')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
             ]
)

@app.get("/")
async def root():
    return {"status": "ok"}


def verify_signature(payload_body, signature_header):
    if not signature_header:
        raise HTTPException(status_code=400, detail="Missing signature")
    hash_object = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = 'sha256=' + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")

def is_excluded(filename: str, masks: list[str]) -> bool:
    for mask in masks:
        if fnmatch.fnmatch(filename, mask):
            return True
    return False


async def process_pull_request(data: dict):
    pr = data.get("pull_request", {})
    repo = data.get("repository", {})
    installation = data.get("installation", {})
    installation_id = installation.get("id")
    action = data.get("action")
    pr_number = pr.get("number")
    repo_full_name = repo.get("full_name")
    head_sha = pr.get("head", {}).get("sha")  # SHA последнего коммита в PR

    # Загружаем конфиг .codereview.yml из репозитория
    config = await get_review_config(installation_id, repo_full_name, head_sha)
    ignore_rules = config.get("ignore", [])
    select_rules = config.get("select", [])
    exclude_masks = config.get("exclude", [])

    logger.info(f"Обрабатываю PR #{pr_number} в {repo_full_name}, действие: {action}")


    try:
        files_data = await get_pull_request_files(installation_id, repo_full_name, pr_number)
    except Exception as e:
        logger.error(f'Не удалось получить список файлов', {e})
        return

    python_files = [
        f for f in files_data
        if f['filename'].endswith('.py')
           and f['status'] != 'removed'
           and not is_excluded(f['filename'], exclude_masks)
    ]
    if not python_files:
        logger.info("Нет Python-файлов для проверки")
        return

    all_problems = []
    for file_info in python_files:
        filename = file_info['filename']
        patch = file_info.get('patch')
        logger.info(f'Анализирую {filename}')
        try:
            content = await get_file_content(installation_id, repo_full_name, filename, ref=head_sha)
            problems = run_ruff(content, filename, ignore_rules=ignore_rules, select_rules=select_rules)
            if patch:
                ranges = parse_diff_ranges(patch)
                filtered = []
                for p in problems:
                    row = p.get('location', {}).get('row')
                    if row is not None and any(start <= row <= end for (start, end) in ranges):
                        p['filename'] = filename
                        filtered.append(p)
                problems = filtered
            else:
                for p in problems:
                    p['filename'] = filename
            all_problems.extend(problems)
        except Exception as e:
            logger.error(f'Ошибка при анализе {filename}: {e}')

    logger.info(f'Найдено {len(all_problems)} проблем(ы)')

    if all_problems:
        body_lines = [
            "## Code Review Bot",
            f'Найдено {len(all_problems)} потенциальных проблем:\n'
        ]
        for problem in all_problems[:10]:
            filename = problem.get('filename', '?')
            location = problem.get('location', {})
            row = location.get('row', '?')
            message = problem.get('message', '?')
            body_lines.append(f'- `{filename}:{row}`- {message}')
        if len(all_problems) > 10:
            body_lines.append(f'\n... и ещё {len(all_problems) - 10} проблем.')

        review_body = '\n'.join(body_lines)

        try:
            await create_pull_request_review(installation_id, repo_full_name, pr_number, review_body)
            logger.info("Ревью успешно опубликовано")
            # === ТЕЛЕГРАМ: УВЕДОМЛЕНИЕ ОБ УСПЕШНОМ РЕВЬЮ ===
            notify_text = (
                f"🤖 <b>Code Review Bot</b>\n"
                f"Репозиторий: <code>{repo_full_name}</code>\n"
                f"PR <a href='https://github.com/{repo_full_name}/pull/{pr_number}'>#{pr_number}</a>: "
                f"{len(all_problems)} замечаний."
            )
            await send_telegram_message(notify_text)

        except Exception as e:
            logger.error(f'Не удалось опубликовать ревью: {e}')
    else:
        logger.info("Проблем не найдено,все чисто!")
        # === ТЕЛЕГРАМ: УВЕДОМЛЕНИЕ О ЧИСТОМ PR ===
        notify_text = (
            f"🤖 <b>Code Review Bot</b>\n"
            f"Репозиторий: <code>{repo_full_name}</code>\n"
            f"PR <a href='https://github.com/{repo_full_name}/pull/{pr_number}'>#{pr_number}</a>: "
            "всё чисто, замечаний нет ✅"
        )
        await send_telegram_message(notify_text)



@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.body()
    signature = request.headers.get('X-Hub-Signature-256')
    verify_signature(payload, signature)

    event = request.headers.get('X-GitHub-Event')
    data = json.loads(payload)

    if event == "ping":
        logger.info("Получен пинг от гитхаб, вебхук работает")
        return {"ok": True}

    if event == "pull_request":
        action = data["action"]
        if action in ("opened", "synchronize", "reopened"):
            asyncio.create_task(process_pull_request(data))
            return {"ok": True}
        else:
            logger.info(f'Действие {action} не обрабатывается')
            return {"ok": True, "ignored": True}

    return {"ok": True}
