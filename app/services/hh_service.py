import httpx
from urllib.parse import urlencode
from typing import List, Optional
from app.config import settings
from app.models import VacancyItem
from app.database import db
from app.logger import logger


class HHService:
    BASE_URL = "https://api.hh.ru"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    def get_auth_url(self, client_id: str, redirect_uri: str) -> str:
        """Генерирует ссылку на вход для конкретного профиля"""
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "negotiations",
        }
        return f"https://hh.ru/oauth/authorize?{urlencode(params)}"

    async def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str) -> Optional[str]:
        """Обменивает код на токен, используя креды профиля"""
        payload = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        try:
            resp = await self.client.post("https://hh.ru/oauth/token", data=payload)
            if resp.status_code == 200:
                return resp.json().get("access_token")
            logger.error(f"Ошибка обмена токена: {resp.text}")
            return None
        except Exception as e:
            logger.error(f"Ошибка сети OAuth: {e}")
            return None

    def _get_headers(self, token: str):
        return {
            "Authorization": f"Bearer {token}",
            "User-Agent": settings.USER_AGENT
        }

    def _check_bad_words(self, title: str, bad_words_str: str) -> bool:
        if not bad_words_str: return True
        bad_list = [w.strip().lower() for w in bad_words_str.split(",") if w.strip()]
        title_lower = title.lower()
        for word in bad_list:
            if word in title_lower: return False
        return True

    async def search_vacancies(self, token: str, query: str, bad_words: str = "", area=113) -> List[VacancyItem]:
        if not token: return []

        params = {"text": query, "area": area, "per_page": 50, "order_by": "publication_time"}
        try:
            resp = await self.client.get(f"{self.BASE_URL}/vacancies", params=params, headers=self._get_headers(token))
            items = resp.json().get("items", [])

            result = []
            for it in items:
                v_id = it.get("id")
                title = it.get("name", "")

                if db.is_applied(v_id): continue
                if not self._check_bad_words(title, bad_words): continue

                emp = (it.get("employer") or {}).get("name", "Unknown")
                loc = (it.get("area") or {}).get("name", "Unknown")

                result.append(VacancyItem(
                    id=v_id, title=title, company=emp, location=loc, link=it.get("alternate_url")
                ))
            return result
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return []

    async def apply_single(self, token: str, vacancy_id: str, resume_id: str, message: str, title: str,
                           company: str) -> bool:
        if not token: return False

        url = f"{self.BASE_URL}/negotiations"
        payload = {"vacancy_id": vacancy_id, "resume_id": resume_id, "message": message}

        try:
            resp = await self.client.post(url, headers=self._get_headers(token), data=payload)
            status = "rejected"
            if resp.status_code == 201:
                status = "accepted"
            elif resp.status_code == 403 and "limit" in resp.text:
                status = "limit_exceeded"

            db.add_history(vacancy_id, title, company, status, message)
            return status == "accepted"
        except Exception as e:
            logger.error(f"Ошибка отклика {vacancy_id}: {e}")
            return False


hh_service = HHService()
