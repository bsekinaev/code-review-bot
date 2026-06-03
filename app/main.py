# app/main.py
import hmac
import hashlib
import json
import logging
from fastapi import FastAPI, HTTPException, Request
from app.tasks.process_pr import process_pr_task
from decouple import config

WEBHOOK_SECRET = config("WEBHOOK_SECRET")
app = FastAPI()

logger = logging.getLogger("uvicorn")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)


@app.get("/")
async def root():
    return {"status": "ok"}


def verify_signature(payload_body, signature_header):
    if not signature_header:
        raise HTTPException(status_code=400, detail="Missing signature")
    hash_object = hmac.new(WEBHOOK_SECRET.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")


@app.post("/webhook")
async def github_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    verify_signature(payload, signature)

    event = request.headers.get("X-GitHub-Event")
    data = json.loads(payload)

    if event == "ping":
        return {"ok": True}

    if event == "pull_request":
        action = data.get("action")
        if action in ("opened", "synchronize", "reopened"):
            # 🔥 Отправляем задачу в очередь Celery через Redis
            process_pr_task.delay(data)
            return {"ok": True}
        return {"ok": True, "ignored": action}

    return {"ok": True}