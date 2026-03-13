"""
Tasks de fetch de dados do Garmin Connect.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from celery import shared_task
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from influxdb import InfluxDBClient
from garminconnect import Garmin
from cryptography.fernet import Fernet
import hashlib
import base64

logger = logging.getLogger(__name__)

DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER', 'allerac')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'allerac_secret')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DB', 'allerac_health')}"
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

influx_client = InfluxDBClient(
    host=os.getenv("INFLUXDB_HOST", "localhost"),
    port=int(os.getenv("INFLUXDB_PORT", "8086")),
    username=os.getenv("INFLUXDB_USER", "allerac"),
    password=os.getenv("INFLUXDB_PASSWORD", "allerac_secret"),
    database=os.getenv("INFLUXDB_DB", "health_metrics"),
)


def get_fernet() -> Fernet:
    encryption_key = os.getenv("ENCRYPTION_KEY", "32-byte-key-for-encryption-here")
    key = hashlib.sha256(encryption_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def decrypt_data(encrypted_data) -> str:
    return get_fernet().decrypt(bytes(encrypted_data)).decode()


def authenticate_garmin(creds) -> Optional[Garmin]:
    """Autentica no Garmin usando session dump salvo pelo garth."""
    try:
        session_dump = decrypt_data(creds.oauth1_token_encrypted)
        garmin = Garmin()
        garmin.garth.loads(session_dump)
        profile = garmin.garth.profile
        garmin.display_name = profile.get("displayName")
        garmin.full_name = profile.get("fullName")
        return garmin
    except Exception as e:
        logger.error(f"Erro ao autenticar: {e}")
        return None


def fetch_and_store_data(garmin: Garmin, user_id: str, start_date, end_date) -> int:
    """Busca dados do Garmin e armazena no InfluxDB."""
    records = 0
    points = []

    total_days = (end_date - start_date).days + 1
    day_num = 0

    current_date = start_date
    while current_date <= end_date:
        day_num += 1
        date_str = current_date.isoformat()
        timestamp = datetime.combine(current_date, datetime.min.time()).isoformat() + "Z"
        logger.info(f"[{day_num}/{total_days}] Buscando dados de {date_str}...")

        try:
            stats = garmin.get_stats(date_str)
            if stats:
                points.append({
                    "measurement": "daily_stats",
                    "tags": {"user_id": user_id},
                    "time": timestamp,
                    "fields": {
                        "steps": float(stats.get("totalSteps") or 0),
                        "calories": float(stats.get("totalKilocalories") or 0),
                        "distance": float(stats.get("totalDistanceMeters") or 0) / 1000,
                        "active_minutes": float((stats.get("moderateIntensityMinutes") or 0) + (stats.get("vigorousIntensityMinutes") or 0)),
                        "floors_climbed": float(stats.get("floorsAscended") or 0),
                    }
                })
                records += 1
        except Exception as e:
            logger.warning(f"daily_stats {date_str}: {e}")

        try:
            sleep = garmin.get_sleep_data(date_str)
            if sleep and sleep.get("dailySleepDTO"):
                s = sleep["dailySleepDTO"]
                points.append({
                    "measurement": "sleep",
                    "tags": {"user_id": user_id},
                    "time": timestamp,
                    "fields": {
                        "duration": float(s.get("sleepTimeSeconds") or 0),
                        "deep": float(s.get("deepSleepSeconds") or 0),
                        "light": float(s.get("lightSleepSeconds") or 0),
                        "rem": float(s.get("remSleepSeconds") or 0),
                        "awake": float(s.get("awakeSleepSeconds") or 0),
                        "score": float((s.get("sleepScores") or {}).get("overall", {}).get("value") or 0),
                    }
                })
                records += 1
        except Exception as e:
            logger.warning(f"sleep {date_str}: {e}")

        try:
            hr = garmin.get_heart_rates(date_str)
            if hr:
                points.append({
                    "measurement": "heart_rate",
                    "tags": {"user_id": user_id},
                    "time": timestamp,
                    "fields": {
                        "resting": float(hr.get("restingHeartRate") or 0),
                        "max": float(hr.get("maxHeartRate") or 0),
                        "avg": float(hr.get("averageHeartRate") or 0),
                    }
                })
                records += 1
        except Exception as e:
            logger.warning(f"heart_rate {date_str}: {e}")

        try:
            stress = garmin.get_stress_data(date_str)
            if stress:
                points.append({
                    "measurement": "stress",
                    "tags": {"user_id": user_id},
                    "time": timestamp,
                    "fields": {
                        "avg": float(stress.get("avgStressLevel") or 0),
                        "max": float(stress.get("maxStressLevel") or 0),
                        "rest_duration": float(stress.get("restStressDuration") or 0),
                    }
                })
                records += 1
        except Exception as e:
            logger.warning(f"stress {date_str}: {e}")

        try:
            bb = garmin.get_body_battery(date_str, date_str)
            if bb and len(bb) > 0:
                day_data = bb[0] if isinstance(bb[0], dict) else None
                if day_data:
                    charged = day_data.get("charged")
                    drained = day_data.get("drained")
                    bb_values = day_data.get("bodyBatteryValuesArray") or []
                    levels = [v[1] for v in bb_values if v and len(v) > 1 and v[1] is not None]
                    points.append({
                        "measurement": "body_battery",
                        "tags": {"user_id": user_id},
                        "time": timestamp,
                        "fields": {
                            "max": float(max(levels)) if levels else 0.0,
                            "min": float(min(levels)) if levels else 0.0,
                            "end": float(levels[-1]) if levels else 0.0,
                            "charged": float(charged or 0),
                            "drained": float(drained or 0),
                        }
                    })
                    records += 1
        except Exception as e:
            logger.warning(f"body_battery {date_str}: {e}")

        current_date += timedelta(days=1)

    if points:
        influx_client.write_points(points)
        logger.info(f"Escrito {len(points)} pontos no InfluxDB para {user_id}")

    return records


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def initial_sync(self, user_id: str):
    """Sync inicial - busca dados dos ultimos 30 dias."""
    logger.info(f"Iniciando sync inicial para usuario {user_id}")

    session = Session()
    try:
        creds = session.execute(
            text("SELECT * FROM garmin_credentials WHERE user_id = :uid"),
            {"uid": user_id}
        ).fetchone()

        if not creds or not creds.is_connected:
            logger.warning(f"Usuario {user_id} sem credenciais validas")
            return {"status": "error", "message": "Credenciais nao encontradas"}

        session.execute(
            text("INSERT INTO sync_jobs (user_id, status, job_type, started_at) VALUES (:uid, 'running', 'full', :started_at)"),
            {"uid": user_id, "started_at": datetime.now(timezone.utc)}
        )
        session.commit()

        garmin = authenticate_garmin(creds)
        if not garmin:
            raise Exception("Falha na autenticacao Garmin")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        records = fetch_and_store_data(garmin, user_id, start_date, end_date)

        session.execute(
            text("UPDATE sync_jobs SET status='completed', completed_at=:t, records_fetched=:r WHERE user_id=:uid AND status='running'"),
            {"uid": user_id, "t": datetime.now(timezone.utc), "r": records}
        )
        session.execute(
            text("UPDATE garmin_credentials SET last_sync_at=:t, last_error=NULL WHERE user_id=:uid"),
            {"uid": user_id, "t": datetime.now(timezone.utc)}
        )
        session.commit()

        logger.info(f"Sync inicial completo para {user_id}: {records} registros")
        return {"status": "success", "records": records}

    except Exception as e:
        logger.error(f"Erro no sync inicial para {user_id}: {e}", exc_info=True)
        try:
            session.execute(
                text("UPDATE sync_jobs SET status='failed', completed_at=:t, error_message=:err WHERE user_id=:uid AND status='running'"),
                {"uid": user_id, "t": datetime.now(timezone.utc), "err": str(e)}
            )
            session.execute(
                text("UPDATE garmin_credentials SET last_error=:err WHERE user_id=:uid"),
                {"uid": user_id, "err": str(e)}
            )
            session.commit()
        except Exception:
            pass
        raise self.retry(exc=e)

    finally:
        session.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def incremental_sync(self, user_id: str):
    """Sync incremental - busca dados do ultimo dia."""
    logger.info(f"Iniciando sync incremental para usuario {user_id}")

    session = Session()
    try:
        creds = session.execute(
            text("SELECT * FROM garmin_credentials WHERE user_id = :uid AND sync_enabled = true"),
            {"uid": user_id}
        ).fetchone()

        if not creds or not creds.is_connected:
            return {"status": "skipped", "message": "Credenciais invalidas ou sync desabilitado"}

        garmin = authenticate_garmin(creds)
        if not garmin:
            raise Exception("Falha na autenticacao Garmin")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=1)
        records = fetch_and_store_data(garmin, user_id, start_date, end_date)

        session.execute(
            text("UPDATE garmin_credentials SET last_sync_at=:t, last_error=NULL WHERE user_id=:uid"),
            {"uid": user_id, "t": datetime.now(timezone.utc)}
        )
        session.commit()

        logger.info(f"Sync incremental completo para {user_id}: {records} registros")
        return {"status": "success", "records": records}

    except Exception as e:
        logger.error(f"Erro no sync incremental para {user_id}: {e}", exc_info=True)
        try:
            session.execute(
                text("UPDATE garmin_credentials SET last_error=:err WHERE user_id=:uid"),
                {"uid": user_id, "err": str(e)}
            )
            session.commit()
        except Exception:
            pass
        raise self.retry(exc=e)

    finally:
        session.close()


@shared_task
def sync_all_users():
    """Dispara sync incremental para todos os usuarios ativos."""
    session = Session()
    try:
        users = session.execute(
            text("SELECT user_id FROM garmin_credentials WHERE is_connected = true AND sync_enabled = true")
        ).fetchall()

        for user in users:
            incremental_sync.delay(str(user.user_id))

        logger.info(f"Disparado sync para {len(users)} usuarios")
        return {"status": "success", "users_queued": len(users)}
    finally:
        session.close()
