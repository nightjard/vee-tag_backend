from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from app.config import settings
import hashlib
import logging
from app.services.email_service import send_otp_email
import random

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    password_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return pwd_context.verify(password_hash, hashed_password)


def get_password_hash(password: str) -> str:
    """Хеширование пароля"""
    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return pwd_context.hash(password_hash)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Создание access token — гарантируем, что sub будет строкой"""
    to_encode = data.copy()
    # Force sub to be a string if present
    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Создание refresh token — гарантируем, что sub будет строкой"""
    to_encode = data.copy()
    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])

    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Декодирование токена с подробным логированием ошибок"""
    try:
        # Покажем непроверенные claim'ы — полезно для диагностики
        try:
            unverified = jwt.get_unverified_claims(token)
            logger.info("Unverified claims: %s", unverified)
        except Exception:
            logger.info("Cannot get unverified claims for token (maybe malformed).")

        logger.info("Predecode token: %s", token)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.info("Decoded JWT payload: %s", payload)
        return payload

    except ExpiredSignatureError as e:
        logger.warning("Token expired: %s", e)
        return None
    except JWTError as e:
        # Подробная причина (bad signature, invalid algorithm и т.д.)
        logger.exception("JWT decode error: %s", e)
        return None
    except Exception as e:
        logger.exception("Unexpected error decoding JWT: %s", e)
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """Проверка токена"""
    payload = decode_token(token)
    logger.info("Verify token: %s", payload)
    if payload is None:
        return None
    
    if payload.get("type") != token_type:
        return None
    
    return payload
