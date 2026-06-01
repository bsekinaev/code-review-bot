import asyncio
import hmac
import hashlib
import json
import logging
import fnmatch
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from sqlalchemy import select
from decouple import config

from app.diff_parser import parse_diff_ranges
from app.github_api import get_pull_request_files, get_file_content, create_pull_request_review
from app.config_loader import get_review_config
from app.linter import run_ruff
from app.telegram_bot import send_telegram_message
from app.db import AsyncSessionLocal
from app.models import Organization, Repository, Review

WEBHOOK_SECRET = config("WEBHOOK_SECRET")
app = FastAPI()

logger = logging.getLogger("uvicorn")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
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
        WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")


def is_excluded(filename: str, masks: list[str]) -> bool:
    for mask in masks:
        if fnmatch.fnmatch(filename, mask):
            return True
    return False


async def _safe_process_pr(data: dict):
    async with AsyncSessionLocal() as db:
        try:
            await process_pull_request(data, db)
            await db.commit()
        except Exception as e:
            logger.error(f"❌ Background task failed: {e}", exc_info=True)
            await db.rollback()


async def process_pull_request(data: dict, db):
    start_time = time.time()

    pr = data.get("pull_request", {})
    repo = data.get("repository", {})
    installation = data.get("installation", {})

    installation_id = installation.get("id")
    repo_full_name = repo.get("full_name")
    pr_number = pr.get("number")
    head_sha = pr.get("head", {}).get("sha")
    repo_github_id = repo.get("id")
    is_private = repo.get("private", False)
    org_github_login = installation.get("account", {}).get("login")

    # Создаём или находим Organization
    org_stmt = select(Organization).where(Organization.installation_id == installation_id)
    result = await db.execute(org_stmt)
    org = result.scalar_one_or_none()
    if not org:
        org = Organization(installation_id=installation_id, github_login=org_github_login)
        db.add(org)
        await db.flush()  # Получаем org.id без коммита

    # Создаём или находим Repository
    repo_stmt = select(Repository).where(Repository.github_id == repo_github_id)
    result = await db.execute(repo_stmt)
    repo_obj = result.scalar_one_or_none()
    if not repo_obj:
        repo_obj = Repository(
            org_id=org.id,
            github_id=repo_github_id,
            full_name=repo_full_name,
            is_private=is_private
        )
        db.add(repo_obj)
        await db.flush()

    # Создаём запись о ревью
    review = Review(
        org_id=org.id,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        commit_sha=head_sha,
        status="processing"
    )
    db.add(review)
    await db.flush()
    review_id = review.id  # Сохраняем ID, если понадобится позже

    # Загружаем конфиг .codereview.yml
    config_dict = await get_review_config(installation_id, repo_full_name, head_sha)
    ignore_rules = config_dict.get("ignore", [])
    select_rules = config_dict.get("select", [])
    exclude_masks = config_dict.get("exclude", [])

    logger.info(f"🔍 Обрабатываю PR #{pr_number} в {repo_full_name}")

    try:
        files_data = await get_pull_request_files(installation_id, repo_full_name, pr_number)
    except Exception as e:
        logger.error(f"Не удалось получить файлы PR: {e}", exc_info=True)
        review.status = "failed"
        review.processing_time_ms = int((time.time() - start_time) * 1000)
        review.completed_at = datetime.now(timezone.utc)
        return

    python_files = [
        f for f in files_data
        if f["filename"].endswith(".py")
           and f["status"] != "removed"
           and not is_excluded(f["filename"], exclude_masks)
    ]

    if not python_files:
        logger.info("Нет Python-файлов для проверки")
        review.status = "completed"
        review.problems_count = 0
        review.processing_time_ms = int((time.time() - start_time) * 1000)
        review.completed_at = datetime.now(timezone.utc)
        return

    all_problems = []
    for file_info in python_files:
        filename = file_info["filename"]
        patch = file_info.get("patch")
        logger.info(f"📄 Анализирую {filename}")

        try:
            content = await get_file_content(installation_id, repo_full_name, filename, ref=head_sha)
            problems = run_ruff(content, filename, ignore_rules=ignore_rules, select_rules=select_rules)

            if patch:
                ranges = parse_diff_ranges(patch)
                filtered = []
                for p in problems:
                    row = p.get("location", {}).get("row")
                    if row is not None and any(start <= row <= end for (start, end) in ranges):
                        p["filename"] = filename
                        filtered.append(p)
                problems = filtered
            else:
                for p in problems:
                    p["filename"] = filename

            all_problems.extend(problems)
        except Exception as e:
            logger.error(f"Ошибка при анализе {filename}: {e}", exc_info=True)

    logger.info(f"✅ Найдено {len(all_problems)} проблем(ы)")

    # Фиксируем результат в БД
    review.status = "completed"
    review.problems_count = len(all_problems)
    review.problems_data = all_problems
    review.processing_time_ms = int((time.time() - start_time) * 1000)
    review.completed_at = datetime.now(timezone.utc)

    # Публикация в GitHub
    if all_problems:
        body_lines = [
            "## 🤖 Code Review Bot",
            f"Найдено {len(all_problems)} потенциальных проблем:\n"
        ]
        for problem in all_problems[:10]:
            loc = problem.get("location", {})
            row = loc.get("row", "?")
            msg = problem.get("message", "?")
            body_lines.append(f"- `{problem.get('filename', '?')}:{row}` — {msg}")
        if len(all_problems) > 10:
            body_lines.append(f"\n... и ещё {len(all_problems) - 10} проблем.")

        try:
            await create_pull_request_review(installation_id, repo_full_name, pr_number, "\n".join(body_lines))
            logger.info("📝 Ревью опубликовано в PR")
        except Exception as e:
            logger.error(f"Не удалось опубликовать ревью: {e}")

    # Уведомление в Telegram
    notify_text = (
        f"🤖 <b>Code Review Bot</b>\n"
        f"Репозиторий: <code>{repo_full_name}</code>\n"
        f"PR <a href='https://github.com/{repo_full_name}/pull/{pr_number}'>#{pr_number}</a>: "
        f"{len(all_problems)} замечаний." if all_problems else "всё чисто ✅"
    )
    await send_telegram_message(notify_text)


@app.post("/webhook")
async def github_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    verify_signature(payload, signature)

    event = request.headers.get("X-GitHub-Event")
    data = json.loads(payload)

    if event == "ping":
        logger.info("📡 Получен пинг от GitHub")
        return {"ok": True}

    if event == "pull_request":
        action = data.get("action")
        if action in ("opened", "synchronize", "reopened"):
            asyncio.create_task(_safe_process_pr(data))
            return {"ok": True}
        return {"ok": True, "ignored": action}

    return {"ok": True}