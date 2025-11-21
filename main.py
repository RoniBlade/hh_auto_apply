from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path

from app.routers.auth import router as auth_router
from app.routers.vacancies import router as vacancies_router
from app.routers.profiles import router as profiles_router
from app.routers.history import router as history_router

app = FastAPI(title="HH Auto Apply API")

# Настройка CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры API
app.include_router(auth_router, prefix="/api")
app.include_router(vacancies_router, prefix="/api")
app.include_router(profiles_router, prefix="/api")
app.include_router(history_router, prefix="/api")

# Раздаем статические файлы (CSS, JS, изображения)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Обработчики для SPA (Single Page Application)
@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

@app.get("/profiles")
async def serve_profiles():
    return FileResponse("static/profiles.html")

@app.get("/history")
async def serve_history():
    return FileResponse("static/history.html")

# API эндпоинты
@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/")
async def root():
    return {"message": "HH Auto Apply API"}

if __name__ == "__main__":
    import uvicorn
    # Убираем reload=True при прямом запуске
    uvicorn.run(app, host="0.0.0.0", port=8000)