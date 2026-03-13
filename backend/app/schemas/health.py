from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class DailyStats(BaseModel):
    date: date
    steps: Optional[float] = None
    calories: Optional[float] = None
    distance: Optional[float] = None
    active_minutes: Optional[float] = None
    floors_climbed: Optional[float] = None


class SleepData(BaseModel):
    date: date
    duration: Optional[float] = None
    deep: Optional[float] = None
    light: Optional[float] = None
    rem: Optional[float] = None
    awake: Optional[float] = None
    score: Optional[float] = None


class HeartRateData(BaseModel):
    date: date
    resting: Optional[float] = None
    max: Optional[float] = None
    avg: Optional[float] = None


class StressData(BaseModel):
    date: date
    avg_stress: Optional[float] = None
    max_stress: Optional[float] = None
    rest_stress_duration: Optional[float] = None


class HRVData(BaseModel):
    date: date
    weekly_avg: Optional[float] = None
    last_night: Optional[float] = None
    status: Optional[str] = None


class BodyBatteryData(BaseModel):
    date: date
    max: Optional[float] = None
    min: Optional[float] = None
    end: Optional[float] = None
    charged: Optional[float] = None
    drained: Optional[float] = None


class HealthMetrics(BaseModel):
    user_id: str
    period_start: date
    period_end: date
    daily_stats: List[DailyStats] = []
    sleep: List[SleepData] = []
    heart_rate: List[HeartRateData] = []
    stress: List[StressData] = []
    hrv: List[HRVData] = []
    body_battery: List[BodyBatteryData] = []
