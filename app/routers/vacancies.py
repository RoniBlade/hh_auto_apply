from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import List
import asyncio
from app.models import VacancyItem, ApplyAllRequest
from app.services.hh_service import hh_service
from app.database import db
from app.logger import logger

router = APIRouter(tags=["Vacancies"])

def get_active_context():
    """Достаем настройки и токен активного профиля"""
    p = db.get_active_profile()
    if not p:
        raise HTTPException(status_code=400, detail="Нет активного профиля")
    if not p['access_token']:
        raise HTTPException(status_code=401, detail="Активный профиль не авторизован (нет токена)")
    return p


@router.get("/vacancies", response_model=List[VacancyItem])
async def search(query: str, area: int = 113):
    """Поиск вакансий по запросу"""
    if not query:
        raise HTTPException(status_code=400, detail="Параметр 'query' обязателен.")

    p = get_active_context()  # Проверка токена
    try:
        # Ищем вакансии через сервис hh_service
        vacancies = await hh_service.search_vacancies(p['access_token'], query, p['bad_words'], area)
        if not vacancies:
            logger.info(f"По запросу '{query}' не найдено вакансий.")
        return vacancies
    except Exception as e:
        logger.error(f"Ошибка поиска вакансий: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка поиска вакансий")


@router.post("/apply-all")
async def apply_all(bg_tasks: BackgroundTasks, req: ApplyAllRequest):
    """Автоотклик на все вакансии по запросу"""
    if not req.query:
        raise HTTPException(status_code=400, detail="Параметр 'query' обязателен.")

    p = get_active_context()
    logger.info(f"Запуск автоотклика для профиля: {p['name']} с запросом: {req.query}")

    async def task(token, r_id, msg, bw, q):
        logger.info(f"START TASK for {p['name']}")
        try:
            # Поиск вакансий
            vacs = await hh_service.search_vacancies(token, q, bw)
            if not vacs:
                logger.warning(f"По запросу '{q}' не найдено вакансий.")
            applied_count = 0  # Счётчик откликов
            for v in vacs:
                # Применяем отклик к каждой вакансии
                if await hh_service.apply_single(token, v.id, r_id, msg, v.title, v.company):
                    applied_count += 1
                await asyncio.sleep(2)  # Задержка между откликами
            logger.info(f"Отклики отправлены на {applied_count} вакансий.")
        except Exception as e:
            logger.error(f"Ошибка выполнения автоотклика: {str(e)}")

        logger.info("END TASK")

    # Добавляем задачу в фоновую очередь
    bg_tasks.add_task(task, p['access_token'], p['resume_id'], p['cover_letter'], p['bad_words'], req.query)
    return {"status": "started"}


@router.post("/apply/{vid}")
async def manual_apply(vid: str):
    """Ручной отклик на вакансию"""
    p = get_active_context()
    try:
        # Пытаемся откликнуться на вакансию
        success = await hh_service.apply_single(p['access_token'], vid, p['resume_id'], p['cover_letter'], "Manual",
                                                "Manual")
        if success:
            logger.info(f"Отклик на вакансию {vid} успешен.")
            return {"status": "success"}
        else:
            raise HTTPException(status_code=400, detail="Ошибка отклика на вакансию")
    except Exception as e:
        logger.error(f"Ошибка отклика на вакансию {vid}: {str(e)}")
        raise HTTPException(status_code=400, detail="Ошибка отклика на вакансию")
