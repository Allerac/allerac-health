import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.database import get_db
from app.core.security import decode_token, decode_token_allerac_one
from app.models.user import User

security = HTTPBearer()


async def _get_or_provision_allerac_one_user(payload: dict, db: AsyncSession) -> User:
    """Find or create a local user from an allerac-one JWT payload.

    allerac-one tokens must include: sub, email.
    name is optional but used when creating the user.
    """
    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="allerac-one token missing email claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        # Auto-provision: create a local user linked to the allerac-one account.
        # No password is set — this account can only be accessed via allerac-one tokens.
        user = User(
            id=uuid.uuid4(),
            email=email,
            name=payload.get("name") or email.split("@")[0],
            password_hash=None,
            oauth_provider="allerac-one",
            oauth_id=payload.get("sub"),
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate request via Bearer token.

    Accepts tokens from two sources:
    - allerac-health (local JWT, signed with SECRET_KEY)
    - allerac-one (signed with ALLERAC_ONE_SECRET_KEY, if configured)
    """
    token = credentials.credentials

    # 1. Try local token first
    payload = decode_token(token)
    if payload is not None:
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")
        return user

    # 2. Try allerac-one token
    payload = decode_token_allerac_one(token)
    if payload is not None:
        if payload.get("iss") != "allerac-one":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await _get_or_provision_allerac_one_user(payload, db)
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Optional authentication — returns None instead of raising on failure."""
    if credentials is None:
        return None

    token = credentials.credentials

    payload = decode_token(token)
    if payload is not None and payload.get("type") == "access":
        user_id = payload.get("sub")
        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user and user.is_active:
                return user

    payload = decode_token_allerac_one(token)
    if payload is not None and payload.get("iss") == "allerac-one":
        try:
            user = await _get_or_provision_allerac_one_user(payload, db)
            if user.is_active:
                return user
        except HTTPException:
            pass

    return None
