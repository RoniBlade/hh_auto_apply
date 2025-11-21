import sqlite3
from datetime import datetime
from typing import List, Optional
from app.config import settings


class Database:
    def __init__(self):
        self.db_name = settings.DB_NAME
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)

    def _init_db(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            # Обновляем таблицу истории, добавляем колонку vacancy_title для хранения названия вакансии
            cur.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vacancy_id TEXT,
                    vacancy_title TEXT,  -- Добавлена колонка для названия вакансии
                    company TEXT,
                    date TEXT,
                    status TEXT,
                    response_text TEXT
                )
            ''')
            # Создание таблицы профилей
            cur.execute('''
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    description TEXT,
                    resume_id TEXT,
                    cover_letter TEXT,
                    bad_words TEXT DEFAULT "",
                    client_id TEXT DEFAULT "",
                    client_secret TEXT DEFAULT "",
                    redirect_uri TEXT DEFAULT "",
                    access_token TEXT DEFAULT "",
                    is_active BOOLEAN DEFAULT 0
                )
            ''')
            conn.commit()

    # --- Profiles --- #
    def create_profile(self, p):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO profiles 
                   (name, description, resume_id, cover_letter, bad_words, client_id, client_secret, redirect_uri, is_active) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                (p.name, p.description, p.resume_id, p.cover_letter, p.bad_words, p.client_id, p.client_secret,
                 p.redirect_uri)
            )
            conn.commit()
            return cur.lastrowid

    def get_profiles(self) -> List[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM profiles")
            return [dict(row) for row in cur.fetchall()]

    def get_profile_by_id(self, pid: int) -> Optional[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM profiles WHERE id = ?", (pid,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_active_profile(self) -> Optional[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM profiles WHERE is_active = 1 LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None

    def set_active_profile(self, profile_id: int):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE profiles SET is_active = 0")
            cur.execute("UPDATE profiles SET is_active = 1 WHERE id = ?", (profile_id,))
            conn.commit()

    def update_token(self, profile_id: int, token: str):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE profiles SET access_token = ? WHERE id = ?", (token, profile_id))
            conn.commit()

    def delete_profile(self, profile_id: int):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
            conn.commit()

    # --- History --- #
    def add_history(self, v_id, title, company, status, text):
        with self._get_conn() as conn:
            cur = conn.cursor()
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            # Вставляем данные с названием вакансии
            cur.execute(
                "INSERT INTO history (vacancy_id, vacancy_title, company, date, status, response_text) VALUES (?, ?, ?, ?, ?, ?)",
                (v_id, title, company, date_str, status, text)
            )
            conn.commit()

    def get_history(self) -> List[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM history ORDER BY id DESC")
            return [dict(row) for row in cur.fetchall()]

    def is_applied(self, v_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM history WHERE vacancy_id = ?", (v_id,))
            return cur.fetchone() is not None


db = Database()
