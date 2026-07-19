from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
import uuid
import structlog

from app.db.session import get_db
from app.auth.models import User, RefreshToken
from app.auth.schemas import (
    UserCreate,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    UserResponse,
)
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/auth", tags=["auth"])
security = HTTPBearer()


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def signup(data: UserCreate, db: AsyncSession = Depends(get_db)):
    logger.info("signup_attempt", email=data.email)

    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        logger.warning("signup_duplicate_email", email=data.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = User(
        email=data.email,
        pw_hash=hash_password(data.password),
        phone_number=data.phone_number,
        timezone=data.timezone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("signup_success", email=user.email, user_id=str(user.id))
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    logger.info("login_attempt", email=data.email)

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.pw_hash):
        logger.warning("login_invalid_credentials", email=data.email)
        raise HTTPException(401, "Invalid credentials")

    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}

    refresh_token = create_refresh_token(token_data)

    db_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(db_token)
    await db.commit()

    logger.info("login_success", email=user.email, user_id=str(user.id))

    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        logger.warning("refresh_invalid_token")
        raise HTTPException(401, "Invalid token")

    logger.info("refresh_attempt", user_id=payload.get("sub"))

    token_hash = hash_token(data.refresh_token)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    db_token = result.scalar_one_or_none()

    if not db_token:
        logger.warning("refresh_token_revoked_or_expired", user_id=payload.get("sub"))
        raise HTTPException(401, "Token revoked or expired")

    db_token.revoked_at = datetime.now(timezone.utc)

    token_data = {
        "sub": payload["sub"],
        "email": payload["email"],
        "role": payload["role"],
    }
    new_refresh = create_refresh_token(token_data)

    new_db_token = RefreshToken(
        user_id=uuid.UUID(payload["sub"]),
        token_hash=hash_token(new_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(new_db_token)
    await db.commit()

    logger.info("refresh_success", user_id=payload["sub"])

    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=new_refresh,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        logger.warning("auth_invalid_access_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("auth_user_not_found", user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    logger.info("get_me", user_id=str(current_user.id))
    return current_user


@router.post("/logout")
async def logout(
    data: TokenRefresh,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info("logout_attempt", user_id=str(current_user.id))

    token_hash = hash_token(data.refresh_token)

    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()

    logger.info("logout_success", user_id=str(current_user.id))

    return {"message": "Logged out"}
