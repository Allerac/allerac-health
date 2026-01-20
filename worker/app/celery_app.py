import os
from celery import Celery
from celery.schedules import crontab

# Configuracao do Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "allerac_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.garmin_fetch", "app.tasks.cleanup"],
)

# Configuracoes
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hora max por task
    task_soft_time_limit=3300,  # Warning apos 55 min
    worker_prefetch_multiplier=1,  # Uma task por vez por worker
    task_acks_late=True,  # Ack apos completar
    task_reject_on_worker_lost=True,
)

# Tarefas agendadas
celery_app.conf.beat_schedule = {
    # Sync incremental a cada hora para usuarios ativos
    "sync-all-users-hourly": {
        "task": "app.tasks.garmin_fetch.sync_all_users",
        "schedule": crontab(minute=0),  # A cada hora
    },
    # Limpeza de sessoes MFA expiradas
    "cleanup-mfa-sessions": {
        "task": "app.tasks.cleanup.cleanup_mfa_sessions",
        "schedule": crontab(minute=30),  # A cada hora, minuto 30
    },
    # Limpeza de jobs antigos
    "cleanup-old-jobs": {
        "task": "app.tasks.cleanup.cleanup_old_jobs",
        "schedule": crontab(hour=3, minute=0),  # Todo dia as 3h
    },
}

if __name__ == "__main__":
    celery_app.start()
