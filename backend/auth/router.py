from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import UserCreate, UserLogin, UserResponse, Token
from backend.auth.service import hash_password, verify_password, create_access_token
from backend.auth.dependencies import get_current_user
from backend.guardrails.rate_limiter import check_login_rate, reset_login_rate
from backend.guardrails.audit_logger import log_rate_limit_blocked

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"

    # ── Guardrail: Login Rate Limiting ────────────────────────────────────────
    rate_result = check_login_rate(ip)
    if not rate_result.allowed:
        log_rate_limit_blocked("/auth/login", None, ip, rate_result.retry_after_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {rate_result.retry_after_seconds}s.",
            headers={"Retry-After": str(rate_result.retry_after_seconds)},
        )

    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")

    reset_login_rate(ip)  # Guardrail: reset counter on successful login
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
