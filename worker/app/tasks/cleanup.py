"""
Tasks de limpeza e manutencao.
"""

import os
import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER', 'allerac')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'allerac_secret')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DB', 'allerac_health')}"
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


@shared_task
def cleanup_mfa_sessions():
    """Remove sessoes MFA expiradas."""
    logger.info("Iniciando limpeza de sessoes MFA expiradas")

    session = Session()
    try:
        result = session.execute(
            text("""
                DELETE FROM mfa_sessions
                WHERE expires_at < :now
                RETURNING id
            """),
            {"now": datetime.now(timezone.utc)}
        )
        deleted = result.rowcount
        session.commit()

        logger.info(f"Removidas {deleted} sessoes MFA expiradas")
        return {"status": "success", "deleted": deleted}

    except Exception as e:
        logger.error(f"Erro ao limpar sessoes MFA: {e}")
        session.rollback()
        return {"status": "error", "message": str(e)}

    finally:
        session.close()


@shared_task
def cleanup_old_jobs():
    """Remove jobs de sync antigos (mais de 30 dias)."""
    logger.info("Iniciando limpeza de jobs antigos")

    session = Session()
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

        result = session.execute(
            text("""
                DELETE FROM sync_jobs
                WHERE created_at < :cutoff
                AND status IN ('completed', 'failed')
                RETURNING id
            """),
            {"cutoff": cutoff_date}
        )
        deleted = result.rowcount
        session.commit()

        logger.info(f"Removidos {deleted} jobs antigos")
        return {"status": "success", "deleted": deleted}

    except Exception as e:
        logger.error(f"Erro ao limpar jobs antigos: {e}")
        session.rollback()
        return {"status": "error", "message": str(e)}

    finally:
        session.close()


@shared_task
def cleanup_inactive_users():
    """
    Desabilita sync para usuarios inativos (sem login em 90 dias).
    Nao deleta dados, apenas para de sincronizar.
    """
    logger.info("Verificando usuarios inativos")

    session = Session()
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)

        result = session.execute(
            text("""
                UPDATE garmin_credentials gc
                SET sync_enabled = false
                FROM users u
                WHERE gc.user_id = u.id
                AND u.updated_at < :cutoff
                AND gc.sync_enabled = true
                RETURNING gc.user_id
            """),
            {"cutoff": cutoff_date}
        )
        disabled = result.rowcount
        session.commit()

        logger.info(f"Desabilitado sync para {disabled} usuarios inativos")
        return {"status": "success", "disabled": disabled}

    except Exception as e:
        logger.error(f"Erro ao verificar usuarios inativos: {e}")
        session.rollback()
        return {"status": "error", "message": str(e)}

    finally:
        session.close()
