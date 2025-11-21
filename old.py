import os
import re
import time
import json
import requests
from urllib.parse import urlencode

# ===================== OAuth =====================

class OAuthCredentials:
    def __init__(self, client_id, client_secret, auth_code=None, redirect_uri=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_code = auth_code
        self.redirect_uri = redirect_uri
        self.access_token = None


# ================== Основной клиент ==================

class HHAutoApply:
    BASE_URL = "https://api.hh.ru"
    OAUTH_URL = "https://hh.ru/oauth/token"      # обмен code -> access_token
    AUTH_URL  = "https://hh.ru/oauth/authorize"  # получение authorization_code

    SEARCH_URL = f"{BASE_URL}/vacancies"         # Поиск вакансий
    APPLY_URL  = f"{BASE_URL}/negotiations"      # Отклик на вакансию

    def __init__(self, credentials: OAuthCredentials, resume_id: str, applied_file: str = "applied_vacancies.txt"):
        self.credentials = credentials
        self.resume_id = resume_id
        self.access_token = None
        self.headers = {}
        self.applied_file = applied_file
        self.applied_vacancies = self._load_applied_vacancies()

    # -------- файл с уже откликнутыми вакансиями --------

    def _load_applied_vacancies(self):
        if os.path.exists(self.applied_file):
            with open(self.applied_file, "r", encoding="utf-8") as f:
                return set(line.strip() for line in f if line.strip())
        return set()

    def _save_applied_vacancy(self, vacancy_id: str):
        with open(self.applied_file, "a", encoding="utf-8") as f:
            f.write(f"{vacancy_id}\n")
        self.applied_vacancies.add(vacancy_id)

    # -------------------- OAuth --------------------

    def authorize(self):
        """
        Выводим ссылку, пользователь логинится и копирует ?code=... с redirect_uri.
        """
        params = {
            "response_type": "code",
            "client_id": self.credentials.client_id,
            "redirect_uri": self.credentials.redirect_uri,
            "scope": "negotiations",  # право откликаться
        }
        auth_url = f"{self.AUTH_URL}?{urlencode(params)}"
        print("🔑 Перейдите по ссылке для авторизации и дайте доступ к откликам:")
        print(auth_url)
        self.credentials.auth_code = input("🔑 Введите значение параметра `code` из redirect_uri: ").strip()

    def get_access_token(self):
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.credentials.client_id,
            "client_secret": self.credentials.client_secret,
            "code": self.credentials.auth_code,
            "redirect_uri": self.credentials.redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = requests.post(self.OAUTH_URL, data=payload, headers=headers, timeout=30)

        if resp.status_code == 200:
            data = resp.json()
            self.credentials.access_token = data.get("access_token")
            self.access_token = self.credentials.access_token
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/119.0.0.0 Safari/537.36"
                )
            }
            print("Авторизация прошла успешно.")
        else:
            print(f"Ошибка авторизации: {resp.status_code} - {resp.text}")
            raise RuntimeError("Не удалось получить access_token")

    # ---------------- Утилиты вывода ----------------

    def _brief(self, it: dict) -> str:
        emp = (it.get("employer") or {}).get("name") or "—"
        area = (it.get("area") or {}).get("name") or "—"
        url  = it.get("alternate_url") or f"https://hh.ru/vacancy/{it.get('id')}"
        return f"[{it.get('id')}] {it.get('name')} — {emp} ({area})\n    {url}"

    # -------------- Локальная фильтрация: ТОЛЬКО НАЗВАНИЕ (чёрный список) ---------------

    def _title_passes_blacklist(self, name: str):
        """
        Фильтр ТОЛЬКО по названию: пропускаем всё, кроме заголовков
        с плохими ключами (аналитика, ML/AI, фронт, фулстек, менеджмент и т.п.).
        Возвращаем (passed: bool, details: str).
        """
        title = (name or "").lower()

        bad = [
            # аналитика/DS/ML/AI
            r"\bаналитик\b", r"\banalyst\b",
            r"\bdata\s*science\b", r"\bdata\s*scientist\b",
            r"\bmachine\s*learning\b", r"\bml\b", r"\bai\b", r"\bllm\b",
            r"\bbi\b", r"\bbusiness\s*intelligence\b", r"\bnlp\b", r"\bcv\b",
            # менеджмент / не-dev
            r"\bменеджер\b", r"\bmanager\b", r"\bproduct\b", r"\bpm\b",
            r"\bteam\s*lead\b", r"\blead\b",
            # фронт/фулстек
            r"\bfull\s*stack\b", r"\bfullstack\b",
            r"\bfrontend\b", r"\breact\b", r"\bvue\b", r"\bangular\b",
            # не Python-направления
            r"\bgolang\b", r"\bnode\.?js\b", r"\berlang\b", r"\bc\+\+\b", r"\bc#\b", r"\b1c\b"
            # тестирование
            r"\bqa\b", r"\bтестировщик\b", r"\bавтотест",
        ]

        hits = [p for p in bad if re.search(p, title)]
        if hits:
            return False, f"Заголовок содержит стоп-слова: {', '.join(hits)}"
        return True, "OK (стоп-слов нет)"

    # ---------------- Поиск вакансий ----------------

    def fetch_vacancies(self,
                        experiences=(None, "between1And3", "between3And6"),
                        area=113,
                        pages=5,
                        per_page=100,
                        period=30,
                        excluded_text=("Менеджер, Аналитик, аналитик, Data, Data Science, ML, AI, "
                                       "Fullstack, LLM, Machine Learn")):
        """
        Поиск Python Backend по трём режимам опыта: None, 1–3, 3–6.
        Результаты объединяются без дублей (по id). Фильтр локально — blacklist по названию.
        """
        if not self.access_token:
            print("❌ Нет access_token. Сначала авторизуйтесь.")
            return []

        role_ids = ["96"]  # Python-разработчик
        base_text = "Java Developer"

        # Небольшая валидация списка experience
        allowed = {None, "between1And3", "between3And6"}
        exp_list = []
        for e in experiences:
            if e in allowed:
                exp_list.append(e)
            else:
                print(f"⚠️ Игнорирую неизвестный experience='{e}' (разрешены: None, between1And3, between3And6)")

        seen_ids = set()
        merged = []

        def _do_query(exp_value, use_excluded: bool):
            label = exp_value if exp_value is not None else "None(любой)"
            print(f"\n===== ▶️ Старт поиска: experience={label}, excluded_text={'ON' if use_excluded else 'OFF'} =====")
            found_here = 0
            total_seen = 0

            for page in range(pages):
                params = {
                    "text": base_text,
                    "search_field": ["name", "company_name", "description"],
                    "area": area,                     # 113 = РФ (1=Москва, 2=СПб)
                    "per_page": per_page,
                    "page": page,
                    "period": period,                 # 1/3/7/30/90
                    "order_by": "publication_time",
                    "professional_role": role_ids,
                    "work_format": ["REMOTE", "HYBRID"],  # если поддерживается
                }
                if exp_value is not None:
                    params["experience"] = exp_value
                if use_excluded and excluded_text:
                    params["excluded_text"] = excluded_text

                resp = requests.get(self.SEARCH_URL, params=params, headers=self.headers, timeout=60)
                print(f"🔎 {resp.url}")
                print(f"📡 Код ответа: {resp.status_code}")
                if resp.status_code != 200:
                    print(f"❌ Ошибка поиска: {resp.status_code} - {resp.text[:400]}")
                    break

                try:
                    data = resp.json()
                except json.JSONDecodeError:
                    print("❌ Ошибка JSON-декодирования выдачи.")
                    print(resp.text[:800])
                    break

                items = data.get("items", [])
                total_seen += len(items)
                print(f"📦 Получено {len(items)} вакансий на странице {page}.")

                for it in items:
                    vid = it.get("id")
                    # Диагностическая карточка
                    print("—", self._brief(it))
                    # Локальный фильтр по названию
                    passed, why = self._title_passes_blacklist(it.get("name", "") or "")
                    print(f"   ⮡ Фильтр (blacklist): {'ПРОШЛА' if passed else 'ОТКЛОНЕНА'} — {why}")

                    if passed and vid not in seen_ids:
                        seen_ids.add(vid)
                        merged.append(it)
                        found_here += 1

                print(f"🧮 На этой странице: всего {len(items)}, добавлено после фильтра {found_here} (накопительно в этом режиме).")
                time.sleep(1.0)

            print(f"📊 Итого для experience={label}: просмотрено {total_seen}, добавлено {found_here}.\n")

        # Стратегия A: с excluded_text
        for exp in exp_list:
            _do_query(exp, use_excluded=True)

        # Стратегия B: если совсем пусто — повторяем все режимы без excluded_text
        if not merged:
            print("↩️ Пусто после первого прохода. Пробуем ретрай без excluded_text по всем режимам опыта.")
            for exp in exp_list:
                _do_query(exp, use_excluded=False)

        print(f"🧷 Сводка: уникальных вакансий после объединения режимов — {len(merged)}.")
        return merged[:200]

    # ---------------- Отклики ----------------

    def apply_to_vacancies(self, vacancies, message=None, delay_seconds=2.0):
        """
        Отклик на список вакансий. Пропускаем уже обработанные и ошибки 400/403.
        """
        if not self.access_token:
            print("❌ Нет access_token. Сначала авторизуйтесь.")
            return

        if message is None:
            message = "Здравствуйте! Заинтересован в вашей вакансии, давайте обсудим детали"

        for v in vacancies:
            vacancy_id = v.get("id")
            vacancy_name = v.get("name", "Без названия")

            if not vacancy_id:
                continue

            if vacancy_id in self.applied_vacancies:
                print(f"⏩ Уже откликались ранее: {vacancy_name} (ID: {vacancy_id}) — пропуск.")
                continue

            url = f"{self.APPLY_URL}?vacancy_id={vacancy_id}"
            payload = {
                "message": message,
                "resume_id": self.resume_id
            }

            try:
                resp = requests.post(url, headers=self.headers, data=payload, timeout=60)
            except requests.RequestException as e:
                print(f"❌ Network error на {vacancy_name} (ID: {vacancy_id}): {e}")
                time.sleep(delay_seconds)
                continue

            if resp.status_code == 201:
                print(f"✅ Успешный отклик: {vacancy_name} (ID: {vacancy_id})")
                self._save_applied_vacancy(vacancy_id)

            elif resp.status_code == 403:
                try:
                    err = resp.json()
                except Exception:
                    err = {}
                desc = (err.get("description") or "").lower()

                if "negotiations limit exceeded" in desc:
                    print("⛔ Достигнут лимит откликов. Останавливаемся.")
                    return
                elif "already applied" in desc:
                    print(f"⚠️ Уже был отклик ранее: {vacancy_name} (ID: {vacancy_id})")
                    self._save_applied_vacancy(vacancy_id)
                elif "must process test" in desc:
                    print(f"⏳ Требуется тестовое задание: {vacancy_name} (ID: {vacancy_id}) — пропуск.")
                else:
                    print(f"❌ 403 Forbidden на {vacancy_name} (ID: {vacancy_id}): {desc or resp.text[:400]}")

            elif resp.status_code == 400:
                print(f"❌ 400 Bad Request на {vacancy_name} (ID: {vacancy_id}) — пропуск.")
                try:
                    print("Причина:", resp.json().get("description"))
                except Exception:
                    pass

            else:
                print(f"❌ Ошибка отклика {resp.status_code} -> {resp.text[:400]}")

            time.sleep(delay_seconds)


# ======================= main.py =======================

if __name__ == "__main__":
    # --- твои креды ---
    CLIENT_ID = "V2KGQ12V5C4PDHCBJBKQNAVVU4RSEE2RRAKPTDKR5OEGR8EMN28QHIRMFBFLPALS"
    CLIENT_SECRET = "JPCA65U4R3QT981HV9QI9O7GJC8DCSVD7MGU150KO0UG9BOD7PHLAGOQDRUBIO6F"
    REDIRECT_URI = "http://localhost:8081/vacancies/authorization"
    # RESUME_ID = "3ebd881cff0f5c45ad0039ed1f37754b547879"
    RESUME_ID = "d51d5a21ff0b1dc0a10039ed1f444861335a70"

    creds = OAuthCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI
    )

    bot = HHAutoApply(creds, RESUME_ID)

    # 1) Авторизация (получение authorization_code вручную)
    bot.authorize()

    # 2) Обмен code -> access_token
    bot.get_access_token()

    # 3) Поиск сразу по трём режимам опыта: None, 1–3, 3–6
    vacancies = bot.fetch_vacancies(
        experiences=(None, "between1And3", "between3And6"),
        area=113,
        pages=5,
        per_page=100,
        period=30,
        excluded_text=("Менеджер, Аналитик, аналитик, Data, Data Science, ML, AI, "
                       "Fullstack, LLM, Machine Learn, Full-Stack", "1С", "Android")
    )

    print(f"🧾 Итог к откликам: {len(vacancies)} вакансий.")

    # 4) Откликаемся
    bot.apply_to_vacancies(vacancies, delay_seconds=2.0)
