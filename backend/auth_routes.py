from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from models import UserCreate, UserResponse, Token
from database import get_user_by_username, get_user_by_email, create_user
from security import (
    get_password_hash,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    logger.info("register | attempt username=%s email=%s", user.username, user.email)

    try:
        if await get_user_by_username(user.username):
            logger.warning("register | username already taken: %s", user.username)
            raise HTTPException(status_code=400, detail="Username already registered.")

        if await get_user_by_email(user.email):
            logger.warning("register | email already in use: %s", user.email)
            raise HTTPException(status_code=400, detail="Email already registered.")

        hashed_password = get_password_hash(user.password)
        user_data = {
            "username": user.username,
            "email": user.email,
            "hashed_password": hashed_password,
        }
        await create_user(user_data)
        logger.info("register | success username=%s", user.username)
        return UserResponse(username=user.username, email=user.email)

    except HTTPException:
        raise  # let FastAPI handle these as-is
    except Exception as exc:
        logger.error("register | unexpected error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Registration failed due to a server error.")


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    logger.info("login | attempt username=%s", form_data.username)

    try:
        user = await get_user_by_username(form_data.username)
        if not user or not verify_password(form_data.password, user["hashed_password"]):
            logger.warning("login | invalid credentials for username=%s", form_data.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token(
            data={"sub": user["username"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        logger.info("login | success username=%s", form_data.username)
        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("login | unexpected error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed due to a server error.")
