from fastapi import APIRouter
from typing import List
from app.models import ProfileDTO, ProfileCreate
from app.database import db

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.get("/", response_model=List[ProfileDTO])
async def get_all_profiles():
    profiles = db.get_profiles()
    result = []
    for p in profiles:
        # Маскируем секрет при отдаче на фронт
        masked_secret = "***" if p['client_secret'] else ""
        has_token = bool(p['access_token'])

        result.append(ProfileDTO(
            id=p['id'], name=p['name'], description=p['description'],
            resume_id=p['resume_id'], cover_letter=p['cover_letter'],
            bad_words=p['bad_words'] or "",
            client_id=p['client_id'],
            client_secret=masked_secret,  # Не отдаем полный секрет
            redirect_uri=p['redirect_uri'],
            is_active=bool(p['is_active']),
            has_token=has_token
        ))
    return result


@router.post("/")
async def create_profile(p: ProfileCreate):
    new_id = db.create_profile(p)
    return {"status": "created", "id": new_id}


@router.post("/{pid}/activate")
async def activate(pid: int):
    db.set_active_profile(pid)
    return {"status": "activated"}


@router.delete("/{pid}")
async def delete(pid: int):
    db.delete_profile(pid)
    return {"status": "deleted"}