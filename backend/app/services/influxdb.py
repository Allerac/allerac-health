"""
Servico de integracao com InfluxDB.
"""

import logging
from datetime import date
from typing import Dict, Any, List
from influxdb import InfluxDBClient

from app.config import get_settings
from app.schemas.health import (
    HealthMetrics,
    DailyStats,
    SleepData,
    HeartRateData,
    StressData,
    HRVData,
    BodyBatteryData,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class InfluxDBService:
    """Servico para leitura de dados do InfluxDB."""

    def __init__(self):
        self.client = InfluxDBClient(
            host=settings.influxdb_host,
            port=settings.influxdb_port,
            username=settings.influxdb_user,
            password=settings.influxdb_password,
            database=settings.influxdb_db,
        )

    async def get_user_metrics(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
    ) -> HealthMetrics:
        """Obter todas as metricas de um usuario em um periodo."""

        # Converter datas para formato InfluxDB
        start_str = start_date.isoformat() + "T00:00:00Z"
        end_str = end_date.isoformat() + "T23:59:59Z"

        metrics = HealthMetrics(
            user_id=user_id,
            period_start=start_date,
            period_end=end_date,
        )

        # Daily stats
        query = f"""
            SELECT * FROM daily_stats
            WHERE user_id = '{user_id}'
            AND time >= '{start_str}' AND time <= '{end_str}'
            ORDER BY time ASC
        """
        result = self.client.query(query)
        for point in result.get_points():
            metrics.daily_stats.append(
                DailyStats(
                    date=point.get("time", "")[:10],
                    steps=point.get("steps"),
                    calories=point.get("calories"),
                    distance=point.get("distance"),
                    active_minutes=point.get("active_minutes"),
                    floors_climbed=point.get("floors_climbed"),
                )
            )

        # Sleep
        query = f"""
            SELECT * FROM sleep
            WHERE user_id = '{user_id}'
            AND time >= '{start_str}' AND time <= '{end_str}'
            ORDER BY time ASC
        """
        result = self.client.query(query)
        for point in result.get_points():
            metrics.sleep.append(
                SleepData(
                    date=point.get("time", "")[:10],
                    duration=point.get("duration"),
                    deep=point.get("deep"),
                    light=point.get("light"),
                    rem=point.get("rem"),
                    awake=point.get("awake"),
                    score=point.get("score"),
                )
            )

        # Heart rate
        query = f"""
            SELECT * FROM heart_rate
            WHERE user_id = '{user_id}'
            AND time >= '{start_str}' AND time <= '{end_str}'
            ORDER BY time ASC
        """
        result = self.client.query(query)
        for point in result.get_points():
            metrics.heart_rate.append(
                HeartRateData(
                    date=point.get("time", "")[:10],
                    resting=point.get("resting"),
                    max=point.get("max"),
                    avg=point.get("avg"),
                )
            )

        # Stress
        query = f"""
            SELECT * FROM stress
            WHERE user_id = '{user_id}'
            AND time >= '{start_str}' AND time <= '{end_str}'
            ORDER BY time ASC
        """
        result = self.client.query(query)
        for point in result.get_points():
            metrics.stress.append(
                StressData(
                    date=point.get("time", "")[:10],
                    avg_stress=point.get("avg"),
                    max_stress=point.get("max"),
                    rest_stress_duration=point.get("rest_duration"),
                )
            )

        # HRV
        query = f"""
            SELECT * FROM hrv
            WHERE user_id = '{user_id}'
            AND time >= '{start_str}' AND time <= '{end_str}'
            ORDER BY time ASC
        """
        result = self.client.query(query)
        for point in result.get_points():
            metrics.hrv.append(
                HRVData(
                    date=point.get("time", "")[:10],
                    weekly_avg=point.get("weekly_avg"),
                    last_night=point.get("last_night"),
                    status=point.get("status"),
                )
            )

        # Body Battery
        query = f"""
            SELECT * FROM body_battery
            WHERE user_id = '{user_id}'
            AND time >= '{start_str}' AND time <= '{end_str}'
            ORDER BY time ASC
        """
        result = self.client.query(query)
        for point in result.get_points():
            metrics.body_battery.append(
                BodyBatteryData(
                    date=point.get("time", "")[:10],
                    max=point.get("max"),
                    min=point.get("min"),
                    end=point.get("end"),
                    charged=point.get("charged"),
                    drained=point.get("drained"),
                )
            )

        return metrics

    async def get_daily_metrics(
        self, user_id: str, metric_date: date
    ) -> Dict[str, Any]:
        """Obter metricas de um dia especifico."""
        date_str = metric_date.isoformat()
        start_str = date_str + "T00:00:00Z"
        end_str = date_str + "T23:59:59Z"

        result = {}

        measurements = ["daily_stats", "sleep", "heart_rate", "stress", "hrv"]

        for measurement in measurements:
            query = f"""
                SELECT * FROM {measurement}
                WHERE user_id = '{user_id}'
                AND time >= '{start_str}' AND time <= '{end_str}'
                LIMIT 1
            """
            query_result = self.client.query(query)
            points = list(query_result.get_points())
            if points:
                result[measurement] = points[0]

        return result

    def _pct_change(self, current, previous) -> float | None:
        """Calcula variacao percentual entre dois periodos."""
        if previous and previous != 0 and current is not None:
            return round(((current - previous) / previous) * 100, 1)
        return None

    async def get_summary(
        self, user_id: str, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Obter resumo agregado de metricas."""
        from datetime import timedelta

        start_str = start_date.isoformat() + "T00:00:00Z"
        end_str = end_date.isoformat() + "T23:59:59Z"

        # Periodo anterior (mesma duração, antes do periodo atual)
        period_days = (end_date - start_date).days
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days)
        prev_start_str = prev_start.isoformat() + "T00:00:00Z"
        prev_end_str = prev_end.isoformat() + "T23:59:59Z"

        summary = {}

        # Media de passos e calorias (periodo atual)
        query = f"""
            SELECT MEAN(steps) as avg_steps, MEAN(calories) as avg_calories
            FROM daily_stats
            WHERE user_id = '{user_id}'
            AND time >= '{start_str}' AND time <= '{end_str}'
        """
        result = self.client.query(query)
        points = list(result.get_points())
        if points:
            summary["steps"] = {"average": points[0].get("avg_steps")}
            summary["calories"] = {"average": points[0].get("avg_calories")}

        # Media do periodo anterior (para comparacao)
        query_prev = f"""
            SELECT MEAN(steps) as avg_steps, MEAN(calories) as avg_calories
            FROM daily_stats
            WHERE user_id = '{user_id}'
            AND time >= '{prev_start_str}' AND time <= '{prev_end_str}'
        """
        result_prev = self.client.query(query_prev)
        points_prev = list(result_prev.get_points())
        prev_steps = points_prev[0].get("avg_steps") if points_prev else None
        prev_calories = points_prev[0].get("avg_calories") if points_prev else None

        # Media de sono
        query = f"""
            SELECT MEAN("duration") as avg_duration, MEAN(score) as avg_score
            FROM sleep
            WHERE user_id = '{user_id}'
            AND time >= '{start_str}' AND time <= '{end_str}'
        """
        result = self.client.query(query)
        points = list(result.get_points())
        if points:
            summary["sleep"] = {
                "avg_duration_hours": (points[0].get("avg_duration") or 0) / 3600,
                "avg_score": points[0].get("avg_score"),
            }

        # Media de frequencia cardiaca
        query = f"""
            SELECT MEAN(resting) as avg_resting, MEAN(avg) as avg_hr
            FROM heart_rate
            WHERE user_id = '{user_id}'
            AND time >= '{start_str}' AND time <= '{end_str}'
        """
        result = self.client.query(query)
        points = list(result.get_points())
        if points:
            summary["heart_rate"] = {
                "avg_resting": points[0].get("avg_resting"),
                "avg_hr": points[0].get("avg_hr"),
            }

        # Media de stress
        query = f"""
            SELECT MEAN(avg) as avg_stress
            FROM stress
            WHERE user_id = '{user_id}'
            AND time >= '{start_str}' AND time <= '{end_str}'
        """
        result = self.client.query(query)
        points = list(result.get_points())
        if points:
            summary["stress"] = {
                "average": points[0].get("avg_stress"),
            }

        avg_steps = summary.get("steps", {}).get("average")
        avg_calories = summary.get("calories", {}).get("average")

        return {
            "user_id": user_id,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "avg_steps": avg_steps,
            "avg_calories": avg_calories,
            "avg_resting_hr": summary.get("heart_rate", {}).get("avg_resting"),
            "avg_sleep_hours": summary.get("sleep", {}).get("avg_duration_hours"),
            "steps_change": self._pct_change(avg_steps, prev_steps),
            "calories_change": self._pct_change(avg_calories, prev_calories),
        }
