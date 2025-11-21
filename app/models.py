from pydantic import BaseModel
from typing import Optional


class VacancyItem(BaseModel):
    id: str
    title: str
    company: str
    location: str
    link: str


class ProfileDTO(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    resume_id: str
    cover_letter: str
    bad_words: str
    client_id: str
    client_secret: str
    redirect_uri: str
    is_active: bool = False
    has_token: bool = False


class ApplyAllRequest(BaseModel):
    query: str
class ProfileCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    resume_id: Optional[str] = ""
    cover_letter: Optional[str] = ""
    bad_words: Optional[str] = ""
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = ""


class HistoryItem(BaseModel):
    id: int
    date: str
    vacancy_id: str  # ID вакансии
    vacancy_title: str  # Название вакансии
    company: str
    status: str
    response_text: Optional[str] = None

class AuthRequest(BaseModel):
    profile_id: int
    auth_code: str
