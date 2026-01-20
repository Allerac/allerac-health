"""
Tasks de fetch de dados do Garmin Connect.
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from influxdb import InfluxDBClient
from garminconnect import Garmin
from cryptography.fernet import Fernet
import hashlib
import base64

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

# InfluxDB setup
influx_client = InfluxDBClient(
    host=os.getenv("INFLUXDB_HOST", "localhost"),
    port=int(os.getenv("INFLUXDB_PORT", "8086")),
    username=os.getenv("INFLUXDB_USER", "allerac"),
    password=os.getenv("INFLUXDB_PASSWORD", "allerac_secret"),
    database=os.getenv("INFLUXDB_DB", "health_metrics"),
)


def get_fernet() -> Fernet:
    """Cria instancia Fernet para descriptografia."""
    encryption_key = os.getenv("ENCRYPTION_KEY", "32-byte-key-for-encryption-here")
    key = hashlib.sha256(encryption_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def decrypt_data(encrypted_data: bytes) -> str:
    """Descriptografa dados."""
    fernet = get_fernet()
    return fernet.decrypt(encrypted_data).decode()


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def initial_sync(self, user_id: str):
    """
    Sync inicial - busca dados dos ultimos 30 dias.
    """
    logger.info(f"Iniciando sync inicial para usuario {user_id}")

    session = Session()
    try:
        # Buscar credenciais
        result = session.execute(
            "SELECT * FROM garmin_credentials WHERE user_id = :user_id",
            {"user_id": user_id}
        )
        creds = result.fetchone()

        if not creds or not creds.is_connected:
            logger.warning(f"Usuario {user_id} nao tem credenciais validas")
            return {"status": "error", "message": "Credenciais nao encontradas"}

        # Criar job de sync
        session.execute(
            """
            INSERT INTO sync_jobs (user_id, status, job_type, started_at)
            VALUES (:user_id, 'running', 'full', :started_at)
            """,
            {"user_id": user_id, "started_at": datetime.now(timezone.utc)}
        )
        session.commit()

        # Autenticar no Garmin
        garmin = authenticate_garmin(creds)

        if not garmin:
            raise Exception("Falha na autenticacao Garmin")

        # Fetch dados dos ultimos 30 dias
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        records = fetch_and_store_data(garmin, user_id, start_date, end_date)

        # Atualizar job como completo
        session.execute(
            """
            UPDATE sync_jobs
            SET status = 'completed', completed_at = :completed_at, records_fetched = :records
            WHERE user_id = :user_id AND status = 'running'
            """,
            {
                "user_id": user_id,
                "completed_at": datetime.now(timezone.utc),
                "records": records,
            }
        )

        # Atualizar last_sync
        session.execute(
            """
            UPDATE garmin_credentials
            SET last_sync_at = :sync_at, last_error = NULL
            WHERE user_id = :user_id
            """,
            {"user_id": user_id, "sync_at": datetime.now(timezone.utc)}
        )
        session.commit()

        logger.info(f"Sync inicial completo para {user_id}: {records} registros")
        return {"status": "success", "records": records}

    except Exception as e:
        logger.error(f"Erro no sync inicial para {user_id}: {e}")

        # Atualizar job com erro
        session.execute(
            """
            UPDATE sync_jobs
            SET status = 'failed', completed_at = :completed_at, error_message = :error
            WHERE user_id = :user_id AND status = 'running'
            """,
            {
                "user_id": user_id,
                "completed_at": datetime.now(timezone.utc),
                "error": str(e),
            }
        )

        # Atualizar credenciais com erro
        session.execute(
            """
            UPDATE garmin_credentials
            SET last_error = :error
            WHERE user_id = :user_id
            """,
            {"user_id": user_id, "error": str(e)}
        )
        session.commit()

        raise self.retry(exc=e)

    finally:
        session.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def incremental_sync(self, user_id: str):
    """
    Sync incremental - busca apenas dados novos (ultimo dia).
    """
    logger.info(f"Iniciando sync incremental para usuario {user_id}")

    session = Session()
    try:
        # Buscar credenciais
        result = session.execute(
            "SELECT * FROM garmin_credentials WHERE user_id = :user_id AND sync_enabled = true",
            {"user_id": user_id}
        )
        creds = result.fetchone()

        if not creds or not creds.is_connected:
            return {"status": "skipped", "message": "Credenciais invalidas ou sync desabilitado"}

        # Autenticar no Garmin
        garmin = authenticate_garmin(creds)

        if not garmin:
            raise Exception("Falha na autenticacao Garmin")

        # Fetch dados do dia anterior e hoje
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=1)

        records = fetch_and_store_data(garmin, user_id, start_date, end_date)

        # Atualizar last_sync
        session.execute(
            """
            UPDATE garmin_credentials
            SET last_sync_at = :sync_at, last_error = NULL
            WHERE user_id = :user_id
            """,
            {"user_id": user_id, "sync_at": datetime.now(timezone.utc)}
        )
        session.commit()

        logger.info(f"Sync incremental completo para {user_id}: {records} registros")
        return {"status": "success", "records": records}

    except Exception as e:
        logger.error(f"Erro no sync incremental para {user_id}: {e}")

        session.execute(
            """
            UPDATE garmin_credentials
            SET last_error = :error
            WHERE user_id = :user_id
            """,
            {"user_id": user_id, "error": str(e)}
        )
        session.commit()

        raise self.retry(exc=e)

    finally:
        session.close()


@shared_task
def sync_all_users():
    """
    Dispara sync incremental para todos os usuarios ativos.
    """
    logger.info("Iniciando sync para todos os usuarios")

    session = Session()
    try:
        result = session.execute(
            """
            SELECT user_id FROM garmin_credentials
            WHERE is_connected = true AND sync_enabled = true
            """
        )
        users = result.fetchall()

        for user in users:
            incremental_sync.delay(str(user.user_id))

        logger.info(f"Disparado sync para {len(users)} usuarios")
        return {"status": "success", "users_queued": len(users)}

    finally:
        session.close()


def authenticate_garmin(creds) -> Optional[Garmin]:
    """Autentica no Garmin usando tokens salvos."""
    try:
        oauth1_token = json.loads(decrypt_data(creds.oauth1_token_encrypted))
        oauth2_token = json.loads(decrypt_data(creds.oauth2_token_encrypted))

        from garth import Client

        client = Client()
        client.oauth1_token = oauth1_token
        client.oauth2_token = oauth2_token

        garmin = Garmin()
        garmin.garth = client

        # Validar tokens
        garmin.get_full_name()

        return garmin

    except Exception as e:
        logger.error(f"Erro ao autenticar: {e}")
        return None


def fetch_and_store_data(garmin: Garmin, user_id: str, start_date, end_date) -> int:
    """Busca dados do Garmin e armazena no InfluxDB."""
    records = 0
    points = []

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.isoformat()
        timestamp = datetime.combine(current_date, datetime.min.time()).isoformat() + "Z"

        try:
            # Daily stats
            stats = garmin.get_stats(date_str)
            if stats:
                points.append({
                    "measurement": "daily_stats",
                    "tags": {"user_id": user_id},
                    "time": timestamp,
                    "fields": {
                        "steps": stats.get("totalSteps", 0),
                        "calories": stats.get("totalKilocalories", 0),
                        "distance": stats.get("totalDistanceMeters", 0) / 1000,
                        "active_minutes": stats.get("moderateIntensityMinutes", 0) + stats.get("vigorousIntensityMinutes", 0),
                        "floors_climbed": stats.get("floorsAscended", 0),
                    }
                })
                records += 1
        except Exception as e:
            logger.warning(f"Erro ao buscar daily stats para {date_str}: {e}")

        try:
            # Sleep
            sleep = garmin.get_sleep_data(date_str)
            if sleep and sleep.get("dailySleepDTO"):
                sleep_data = sleep["dailySleepDTO"]
                points.append({
                    "measurement": "sleep",
                    "tags": {"user_id": user_id},
                    "time": timestamp,
                    "fields": {
                        "duration": sleep_data.get("sleepTimeSeconds", 0),
                        "deep": sleep_data.get("deepSleepSeconds", 0),
                        "light": sleep_data.get("lightSleepSeconds", 0),
                        "rem": sleep_data.get("remSleepSeconds", 0),
                        "awake": sleep_data.get("awakeSleepSeconds", 0),
                        "score": sleep_data.get("sleepScores", {}).get("overall", {}).get("value", 0),
                    }
                })
                records += 1
        except Exception as e:
            logger.warning(f"Erro ao buscar sleep para {date_str}: {e}")

        try:
            # Heart rate
            hr = garmin.get_heart_rates(date_str)
            if hr:
                points.append({
                    "measurement": "heart_rate",
                    "tags": {"user_id": user_id},
                    "time": timestamp,
                    "fields": {
                        "resting": hr.get("restingHeartRate", 0),
                        "max": hr.get("maxHeartRate", 0),
                        "avg": hr.get("averageHeartRate", 0),
                    }
                })
                records += 1
        except Exception as e:
            logger.warning(f"Erro ao buscar heart rate para {date_str}: {e}")

        try:
            # Stress
            stress = garmin.get_stress_data(date_str)
            if stress:
                points.append({
                    "measurement": "stress",
                    "tags": {"user_id": user_id},
                    "time": timestamp,
                    "fields": {
                        "avg": stress.get("avgStressLevel", 0),
                        "max": stress.get("maxStressLevel", 0),
                        "rest_duration": stress.get("restStressDuration", 0),
                    }
                })
                records += 1
        except Exception as e:
            logger.warning(f"Erro ao buscar stress para {date_str}: {e}")

        current_date += timedelta(days=1)

    # Escrever no InfluxDB
    if points:
        influx_client.write_points(points)

    return records
