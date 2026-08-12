from fastapi import FastAPI
from sqlalchemy import text
from app.config import settings
from app.database import async_session

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello! Your FinGuardian AI backend is alive."}

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.app_env}

@app.get("/db-check")
async def db_check():
    async with async_session() as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()
    return {"database": "connected", "result": value}