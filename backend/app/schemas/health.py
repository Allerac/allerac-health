from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


class DailyStats(BaseModel):
    """Estatisticas diarias."""
    date: date
    steps: Optional[int] = None
    calories: Optional[int] = None
    distance: Optional[float] = None  # km
    active_minutes: Optional[int] = None
    floors_climbed: Optional[int] = None


class SleepData(BaseModel):
    """Dados de sono."""
    date: date
    duration_seconds: Optional[int] = None
    deep_sleep_seconds: Optional[int] = None
    light_sleep_seconds: Optional[int] = None
    rem_sleep_seconds: Optional[int] = None
    awake_seconds: Optional[int] = None
    sleep_score: Optional[int] = None


class HeartRateData(BaseModel):
    """Dados de frequencia cardiaca."""
    date: date
    resting_hr: Optional[int] = None
    max_hr: Optional[int] = None
    avg_hr: Optional[int] = None


class StressData(BaseModel):
    """Dados de stress."""
    date: date
    avg_stress: Optional[int] = None
    max_stress: Optional[int] = None
    rest_stress_duration: Optional[int] = None


class HRVData(BaseModel):
    """Dados de variabilidade cardiaca."""
    date: date
    weekly_avg: Optional[float] = None
    last_night: Optional[float] = None
    status: Optional[str] = None


class HealthMetrics(BaseModel):
    """Resposta com metricas de saude."""
    user_id: str
    period_start: date
    period_end: date
    daily_stats: List[DailyStats] = []
    sleep: List[SleepData] = []
    heart_rate: List[HeartRateData] = []
    stress: List[StressData] = []
    hrv: List[HRVData] = []
