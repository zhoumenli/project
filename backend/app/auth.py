"""Authentication helpers: password hashing, validation rules, token handling."""
import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from . import models
from .database import SessionLocal

# ---- Password hashing: PBKDF2-HMAC-SHA256 with per-user random salt (stdlib only) ----
PBKDF2_ROUNDS = 210_000
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")

# ---- Session idle timeout: no API activity for N minutes -> token revoked ----
# 默认 30 分钟，可用环境变量 SESSION_IDLE_MINUTES 调整（设 0 表示不限制）
IDLE_TIMEOUT_MINUTES = max(0, int(os.getenv("SESSION_IDLE_MINUTES", "30")))
IDLE_TIMEOUT_SECONDS = IDLE_TIMEOUT_MINUTES * 60
# 活跃时间戳的最小写回间隔，避免每个请求都 UPDATE 一次数据库
TOUCH_INTERVAL_SECONDS = 60


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def validate_username(username: str) -> Optional[str]:
    if not username or not USERNAME_RE.match(username):
        return "用户名需为 3-20 位字母、数字或下划线"
    return None


def validate_password(password: str) -> Optional[str]:
    if not password or len(password) < 8 or len(password) > 32:
        return "密码需为 8-32 位"
    if not re.search(r"[a-z]", password):
        return "密码需包含小写字母"
    if not re.search(r"[A-Z]", password):
        return "密码需包含大写字母"
    if not re.search(r"\d", password):
        return "密码需包含数字"
    return None


def create_token(db: Session, user_id: int, ttl_days: int = 30) -> str:
    token = secrets.token_urlsafe(32)
    rec = models.AuthToken(
        token=token,
        user_id=user_id,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(days=ttl_days),
        last_active_at=datetime.now(),
    )
    db.add(rec)
    db.commit()
    return token


def touch_token(db: Session, rec: models.AuthToken) -> None:
    """刷新 token 的最后活跃时间（带节流，避免高频写库）。"""
    if IDLE_TIMEOUT_MINUTES <= 0:
        return
    now = datetime.now()
    if rec.last_active_at and (now - rec.last_active_at).total_seconds() < TOUCH_INTERVAL_SECONDS:
        return
    rec.last_active_at = now
    db.commit()


def resolve_token(db: Session, token: str):
    """校验 Bearer token。

    返回 (token_rec, user, error_detail, error_code)；校验通过时前两项非空。
    空闲超时（IDLE_TIMEOUT_MINUTES 内无任何操作）会直接吊销该 token。
    """
    rec = db.query(models.AuthToken).filter(models.AuthToken.token == token).first()
    if not rec:
        return None, None, "无效的登录凭证", "invalid_token"
    if rec.expires_at and rec.expires_at < datetime.now():
        db.delete(rec)
        db.commit()
        return None, None, "登录已过期，请重新登录", "expired"

    if IDLE_TIMEOUT_MINUTES > 0:
        # 老数据没有 last_active_at 时，用 created_at 兜底，避免历史 token 立即失效
        last = rec.last_active_at or rec.created_at
        if last and (datetime.now() - last).total_seconds() > IDLE_TIMEOUT_SECONDS:
            db.delete(rec)
            db.commit()
            return None, None, "长时间未操作，已自动退出登录", "idle_timeout"

    user = db.query(models.User).filter(models.User.id == rec.user_id).first()
    if not user:
        db.delete(rec)
        db.commit()
        return None, None, "用户不存在", "no_user"

    touch_token(db, rec)
    return rec, user, None, None


def get_current_user(authorization: Optional[str] = Header(None)):
    """FastAPI dependency: require a valid Bearer token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "未登录或登录已过期")
    token = authorization[7:].strip()
    db = SessionLocal()
    try:
        rec, user, detail, code = resolve_token(db, token)
        if not rec:
            raise HTTPException(
                status_code=401,
                detail=detail,
                headers={"X-Auth-Error": code},
            )
        return {"id": user.id, "username": user.username, "role": user.role}
    finally:
        db.close()
