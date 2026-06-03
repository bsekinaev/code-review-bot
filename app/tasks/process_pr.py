import asyncio
import fnmatch
import logging
import time
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import Organization, Repository, Review
from app.github_api import get_pull_request_files, get_file_content, create_pull_request_review
from app.config_loader import get_review_config
from app.linter import run_ruff
from app.diff_parser import parse_diff_ranges
from app.telegram_bot import send_telegram_message

logger = logging.getLogger("uvicorn")


def _is_excluded(filename: str, masks: list[str]) -> bool:
    return any(fnmatch.fnmatch(filename, mask) for mask in masks)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True,
    retry_jitter=True,
)
def process_pr_task(self, data: dict):

    async def _run_async():
        async with AsyncSessionLocal() as db:
            try:
                await _execute_pr_logic(data, db)
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    try:
        asyncio.run(_run_async())
    except Exception as exc:
        # Экспоненциальная задержка: 30s -> 60s -> 120s
        countdown = 30 * (2 ** self.request.retries)
        logger.warning(f"⚠️ Task failed, retrying in {countdown}s...")
        self.retry(exc=exc, countdown=countdown)


async def _execute_pr_logic(data: dict, db):
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

    # 1️⃣ Organization
    org_stmt = select(Organization).where(Organization.installation_id == installation_id)
    result = await db.execute(org_stmt)
    org = result.scalar_one_or_none()
    if not org:
        org = Organization(installation_id=installation_id, github_login=org_github_login)
        db.add(org)
        await db.flush()

    # 2️⃣ Repository
    repo_stmt = select(Repository).where(Repository.github_id == repo_github_id)
    result = await db.execute(repo_stmt)
    repo_obj = result.scalar_one_or_none()
    if not repo_obj:
        repo_obj = Repository(
            org_id=org.id, github_id=repo_github_id,
            full_name=repo_full_name, is_private=is_private
        )
        db.add(repo_obj)
        await db.flush()

    # 3️⃣ Review запись
    review = Review(
        org_id=org.id, repo_full_name=repo_full_name,
        pr_number=pr_number, commit_sha=head_sha, status="processing"
    )
    db.add(review)
    await db.flush()

    config_dict = await get_review_config(installation_id, repo_full_name, head_sha)
    ignore_rules = config_dict.get("ignore", [])
    select_rules = config_dict.get("select", [])
    exclude_masks = config_dict.get("exclude", [])

    logger.info(f"🔍 Celery task: PR #{pr_number} в {repo_full_name}")

    try:
        files_data = await get_pull_request_files(installation_id, repo_full_name, pr_number)
    except Exception as e:
        logger.error(f"❌ Не удалось получить файлы PR: {e}", exc_info=True)
        review.status = "failed"
        review.processing_time_ms = int((time.time() - start_time) * 1000)
        review.completed_at = datetime.now(timezone.utc)
        return

    python_files = [
        f for f in files_data
        if f["filename"].endswith(".py")
           and f["status"] != "removed"
           and not _is_excluded(f["filename"], exclude_masks)
    ]

    if not python_files:
        review.status = "completed"
        review.problems_count = 0
        review.processing_time_ms = int((time.time() - start_time) * 1000)
        review.completed_at = datetime.now(timezone.utc)
        return

    all_problems = []
    for file_info in python_files:
        filename = file_info["filename"]
        patch = file_info.get("patch")

        try:
            content = await get_file_content(installation_id, repo_full_name, filename, ref=head_sha)
            problems = run_ruff(content, filename, ignore_rules=ignore_rules, select_rules=select_rules)

            if patch:
                ranges = parse_diff_ranges(patch)
                filtered = [
                    p for p in problems
                    if (row := p.get("location", {}).get("row")) and any(s <= row <= e for s, e in ranges)
                ]
                for p in filtered: p["filename"] = filename
                problems = filtered
            else:
                for p in problems: p["filename"] = filename

            all_problems.extend(problems)
        except Exception as e:
            logger.error(f"Ошибка при анализе {filename}: {e}")

    review.status = "completed"
    review.problems_count = len(all_problems)
    review.problems_data = all_problems
    review.processing_time_ms = int((time.time() - start_time) * 1000)
    review.completed_at = datetime.now(timezone.utc)

    if all_problems:
        body_lines = ["## 🤖 Code Review Bot", f"Найдено {len(all_problems)} проблем:\n"]
        for p in all_problems[:10]:
            loc = p.get("location", {})
            body_lines.append(f"- `{p.get('filename')}:{loc.get('row', '?')}` — {p.get('message', '?')}")
        if len(all_problems) > 10:
            body_lines.append(f"\n... и ещё {len(all_problems) - 10}.")

        try:
            await create_pull_request_review(installation_id, repo_full_name, pr_number, "\n".join(body_lines))
        except Exception as e:
            logger.error(f"Не удалось опубликовать ревью: {e}")

    await send_telegram_message(
        f"🤖 <b>Code Review Bot</b>\n"
        f"Репозиторий: <code>{repo_full_name}</code>\n"
        f"PR #{pr_number}: {len(all_problems)} замечаний." if all_problems else "всё чисто ✅"
    )