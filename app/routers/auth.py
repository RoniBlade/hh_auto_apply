from fastapi import APIRouter, HTTPException
from app.models import AuthRequest
from app.services.hh_service import hh_service
from app.database import db
import logging

# Настроим логирование
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/link/{profile_id}")
async def get_auth_link(profile_id: int):
    """Генерирует ссылку на основе ClientID из БД"""
    logger.info(f"Получение ссылки для профиля с ID: {profile_id}")

    p = db.get_profile_by_id(profile_id)
    if not p:
        logger.error(f"Профиль с ID {profile_id} не найден")
        raise HTTPException(404, "Профиль не найден")

    if not p['client_id'] or not p['redirect_uri']:
        logger.error(f"В профиле {profile_id} отсутствуют client_id или redirect_uri")
        raise HTTPException(400, "В профиле не заполнены Client ID или Redirect URI")

    url = hh_service.get_auth_url(p['client_id'], p['redirect_uri'])
    logger.info(f"Генерация ссылки: {url}")

    return {"url": url}


@router.post("/token")
async def auth_token(req: AuthRequest):
    """Получает токен и СОХРАНЯЕТ его в профиль в БД"""
    logger.info(f"Received token request: {req}")

    # Ищем профиль по ID
    p = db.get_profile_by_id(req.profile_id)
    if not p:
        logger.error(f"Профиль с ID {req.profile_id} не найден в базе данных")
        raise HTTPException(404, "Профиль не найден")

    # Получаем токен, обменивая код
    logger.info(f"Обмен кода на токен для профиля {req.profile_id}")
    token = await hh_service.exchange_code(
        req.auth_code, p['client_id'], p['client_secret'], p['redirect_uri']
    )

    if token:
        logger.info(f"Токен получен для профиля {req.profile_id}")
        db.update_token(req.profile_id, token)
        return {"status": "authorized"}

    logger.error(f"Не удалось получить токен для профиля {req.profile_id}")
    raise HTTPException(400, "Не удалось получить токен HH")
