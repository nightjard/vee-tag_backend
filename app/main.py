from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db
from app.routers import auth, devices, sos, bookings, chat, volunteers, users, notifications, reviews, qr_medcard

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events для приложения"""
    # Startup
    logger.info("Starting up application...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down application...")


# Создаем приложение
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API для системы помощи пожилым",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": 500,
            "error": {
                "message": "Internal server error",
                "details": str(exc)
            }
        }
    )


# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Подключаем роутеры
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(devices.router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(sos.router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(bookings.router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(chat.router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(volunteers.router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(notifications.router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(reviews.router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(qr_medcard.router, prefix=f"{settings.API_V1_PREFIX}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
