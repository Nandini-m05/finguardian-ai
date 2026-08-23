from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import async_session, get_db
from app.models import User
from app.schemas import UserCreate, UserOut
from app.security import hash_password, verify_password, create_access_token
from app.dependencies import get_current_user
from app.dependencies import get_current_user, require_role

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

@app.post("/login")
async def login(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/admin-only")
async def admin_only_route(current_user: User = Depends(require_role("admin"))):
    return {"message": f"Welcome, admin {current_user.email}"}

