from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date, timedelta

from app.api.deps import get_current_user
from app.models.user import User
from app.services.influxdb import InfluxDBService
from app.schemas.health import HealthMetrics

router = APIRouter()


@router.get("/metrics", response_model=HealthMetrics)
async def get_health_metrics(
    start_date: date = Query(
        default=None, description="Data inicial (padrao: 30 dias atras)"
    ),
    end_date: date = Query(default=None, description="Data final (padrao: hoje)"),
    current_user: User = Depends(get_current_user),
):
    """Obter metricas de saude do usuario."""
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="Data inicial deve ser anterior a data final",
        )

    influx_service = InfluxDBService()

    try:
        metrics = await influx_service.get_user_metrics(
            user_id=str(current_user.id),
            start_date=start_date,
            end_date=end_date,
        )
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar metricas: {str(e)}",
        )


@router.get("/daily/{metric_date}")
async def get_daily_metrics(
    metric_date: date,
    current_user: User = Depends(get_current_user),
):
    """Obter metricas de um dia especifico."""
    influx_service = InfluxDBService()

    try:
        metrics = await influx_service.get_daily_metrics(
            user_id=str(current_user.id),
            metric_date=metric_date,
        )
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar metricas: {str(e)}",
        )


@router.get("/summary")
async def get_summary(
    period: str = Query(default="week", pattern="^(week|month|year)$"),
    current_user: User = Depends(get_current_user),
):
    """Obter resumo de metricas por periodo."""
    end_date = date.today()

    if period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    else:  # year
        start_date = end_date - timedelta(days=365)

    influx_service = InfluxDBService()

    try:
        summary = await influx_service.get_summary(
            user_id=str(current_user.id),
            start_date=start_date,
            end_date=end_date,
        )
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar resumo: {str(e)}",
        )
