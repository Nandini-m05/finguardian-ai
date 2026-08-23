from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import async_session, get_db
from app.models import User
from app.schemas import UserCreate, UserOut
from app.security import hash_password

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

@app.post("/register", response_model=UserOut)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user
 