from fastapi import APIRouter, HTTPException
from typing import List
from app.models import HistoryItem
from app.database import db
from app.logger import logger

router = APIRouter(tags=["History"])

@router.get("/history", response_model=List[HistoryItem])
async def get_history():
    history_data = db.get_history()  # Получаем историю откликов
    history_items = []

    for row in history_data:
        # Проверяем, что поле 'vacancy_id' существует в данных и оно не пустое
        if 'vacancy_id' not in row or not row['vacancy_id']:
            raise HTTPException(status_code=400, detail="Отсутствует vacancy_id в данных истории")

        # Проверяем, что поле 'vacancy_title' существует и оно не пустое
        if 'vacancy_title' not in row or not row['vacancy_title']:
            raise HTTPException(status_code=400, detail="Отсутствует vacancy_title в данных истории")


        # Преобразуем строку данных в модель HistoryItem
        try:
            history_items.append(HistoryItem(**row))
        except Exception as e:
            # Логирование ошибки, если преобразование в модель не удалось
            raise HTTPException(status_code=400, detail=f"Ошибка при обработке данных истории: {str(e)}")

    return history_items
