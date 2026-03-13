from fastapi import APIRouter, Depends, HTTPException, status
from celery import Celery
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.security import encrypt_data, decrypt_data
from app.api.deps import get_current_user
from app.models.user import User
from app.models.garmin import GarminCredentials, MFASession
from app.schemas.garmin import GarminConnect, GarminMFA, GarminStatus
from app.services.garmin import GarminService

router = APIRouter()

_celery = Celery(broker=os.getenv("REDIS_URL", "redis://redis:6379/0"))


@router.get("/status", response_model=GarminStatus)
async def get_garmin_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Garmin connection status."""
    result = await db.execute(
        select(GarminCredentials).where(GarminCredentials.user_id == current_user.id)
    )
    creds = result.scalar_one_or_none()

    if not creds:
        return GarminStatus(
            is_connected=False,
            mfa_pending=False,
            sync_enabled=False,
        )

    return GarminStatus(
        is_connected=creds.is_connected,
        mfa_pending=creds.mfa_pending,
        last_sync_at=creds.last_sync_at,
        last_error=creds.last_error,
        sync_enabled=creds.sync_enabled,
    )


@router.post("/connect", response_model=GarminStatus)
async def connect_garmin(
    data: GarminConnect,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Connect Garmin account."""
    garmin_service = GarminService()

    try:
        # Try to authenticate
        result = await garmin_service.authenticate(data.email, data.password)

        if result["status"] == "mfa_required":
            # MFA required - save temporary session
            session_data = encrypt_data(result["session_data"])

            # Check if MFA session already exists
            mfa_result = await db.execute(
                select(MFASession).where(MFASession.user_id == current_user.id)
            )
            mfa_session = mfa_result.scalar_one_or_none()

            if mfa_session:
                mfa_session.garmin_email = data.email
                mfa_session.session_data = session_data
                mfa_session.expires_at = datetime.now(timezone.utc) + timedelta(
                    minutes=10
                )
            else:
                mfa_session = MFASession(
                    user_id=current_user.id,
                    garmin_email=data.email,
                    session_data=session_data,
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
                )
                db.add(mfa_session)

            # Update/create credentials
            creds_result = await db.execute(
                select(GarminCredentials).where(
                    GarminCredentials.user_id == current_user.id
                )
            )
            creds = creds_result.scalar_one_or_none()

            if creds:
                creds.email_encrypted = encrypt_data(data.email)
                creds.mfa_pending = True
                creds.is_connected = False
            else:
                creds = GarminCredentials(
                    user_id=current_user.id,
                    email_encrypted=encrypt_data(data.email),
                    mfa_pending=True,
                    is_connected=False,
                )
                db.add(creds)

            await db.flush()

            return GarminStatus(
                is_connected=False,
                mfa_pending=True,
                sync_enabled=False,
                message=result.get(
                    "message", "Please check your email or phone for MFA code."
                ),
            )

        elif result["status"] == "success":
            # Login successful - save tokens
            creds_result = await db.execute(
                select(GarminCredentials).where(
                    GarminCredentials.user_id == current_user.id
                )
            )
            creds = creds_result.scalar_one_or_none()

            session_dump = result.get("session_dump", "{}")

            if creds:
                creds.email_encrypted = encrypt_data(data.email)
                creds.oauth1_token_encrypted = encrypt_data(session_dump)
                creds.oauth2_token_encrypted = encrypt_data("{}")
                creds.is_connected = True
                creds.mfa_pending = False
                creds.last_error = None
            else:
                creds = GarminCredentials(
                    user_id=current_user.id,
                    email_encrypted=encrypt_data(data.email),
                    oauth1_token_encrypted=encrypt_data(session_dump),
                    oauth2_token_encrypted=encrypt_data("{}"),
                    is_connected=True,
                    mfa_pending=False,
                )
                db.add(creds)

            await db.flush()

            # TODO: Trigger initial sync job
            # celery_app.send_task("tasks.garmin_fetch.initial_sync", args=[str(current_user.id)])

            return GarminStatus(
                is_connected=True,
                mfa_pending=False,
                sync_enabled=True,
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error connecting to Garmin: {str(e)}",
        )


@router.post("/mfa", response_model=GarminStatus)
async def submit_mfa(
    data: GarminMFA,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit MFA code."""
    # Find MFA session
    result = await db.execute(
        select(MFASession).where(MFASession.user_id == current_user.id)
    )
    mfa_session = result.scalar_one_or_none()

    if not mfa_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending MFA session",
        )

    if mfa_session.expires_at < datetime.now(timezone.utc):
        await db.delete(mfa_session)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA session expired. Please try connecting again.",
        )

    garmin_service = GarminService()

    try:
        session_data = decrypt_data(mfa_session.session_data)
        result = await garmin_service.complete_mfa(session_data, data.mfa_code)

        if result["status"] == "success":
            # Update credentials
            creds_result = await db.execute(
                select(GarminCredentials).where(
                    GarminCredentials.user_id == current_user.id
                )
            )
            creds = creds_result.scalar_one_or_none()

            if creds:
                creds.oauth1_token_encrypted = encrypt_data(
                    result.get("session_dump", "{}")
                )
                creds.oauth2_token_encrypted = encrypt_data("{}")
                creds.is_connected = True
                creds.mfa_pending = False
                creds.last_error = None

            # Clear MFA session
            await db.delete(mfa_session)
            await db.flush()

            # TODO: Trigger initial sync job
            # celery_app.send_task("tasks.garmin_fetch.initial_sync", args=[str(current_user.id)])

            return GarminStatus(
                is_connected=True,
                mfa_pending=False,
                sync_enabled=True,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MFA code",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error validating MFA: {str(e)}",
        )


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dispara sync manual dos dados Garmin."""
    result = await db.execute(
        select(GarminCredentials).where(GarminCredentials.user_id == current_user.id)
    )
    creds = result.scalar_one_or_none()

    if not creds or not creds.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Garmin nao conectado",
        )

    _celery.send_task(
        "app.tasks.garmin_fetch.initial_sync",
        args=[str(current_user.id)],
    )

    return {"message": "Sync iniciado"}


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_garmin(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Garmin account."""
    result = await db.execute(
        select(GarminCredentials).where(GarminCredentials.user_id == current_user.id)
    )
    creds = result.scalar_one_or_none()

    if creds:
        await db.delete(creds)

    # Clear MFA session if exists
    mfa_result = await db.execute(
        select(MFASession).where(MFASession.user_id == current_user.id)
    )
    mfa_session = mfa_result.scalar_one_or_none()
    if mfa_session:
        await db.delete(mfa_session)

    return None
