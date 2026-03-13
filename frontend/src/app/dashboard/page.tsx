'use client'

import { useState, useEffect } from 'react'
import { format, subDays } from 'date-fns'
import {
  Footprints,
  Flame,
  Heart,
  Moon,
  Loader2,
  AlertCircle,
  Watch,
  RefreshCw,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { MetricCard } from '@/components/charts/metric-card'
import { ActivityChart } from '@/components/charts/activity-chart'
import { HeartRateChart } from '@/components/charts/heart-rate-chart'
import { SleepChart } from '@/components/charts/sleep-chart'
import { BodyBatteryChart } from '@/components/charts/body-battery-chart'
import { healthApi, garminApi } from '@/lib/api'
import Link from 'next/link'

type Period = 'day' | 'week' | 'month' | 'year'

interface DailyMetric {
  date: string
  steps: number
  calories: number
  distance: number
}

interface HeartRateMetric {
  date: string
  resting: number
  avg: number
  max: number
}

interface SleepMetric {
  date: string
  deep: number
  light: number
  rem: number
  awake: number
  total: number
}

interface BodyBatteryMetric {
  date: string
  max: number
  min: number
  end: number
}

interface Summary {
  avg_steps: number
  avg_calories: number
  avg_resting_hr: number
  avg_sleep_hours: number
  steps_change: number
  calories_change: number
}

export default function DashboardPage() {
  const [period, setPeriod] = useState<Period>('week')
  const [isLoading, setIsLoading] = useState(true)
  const [isGarminConnected, setIsGarminConnected] = useState<boolean | null>(null)
  const [dailyMetrics, setDailyMetrics] = useState<DailyMetric[]>([])
  const [heartRateMetrics, setHeartRateMetrics] = useState<HeartRateMetric[]>([])
  const [sleepMetrics, setSleepMetrics] = useState<SleepMetric[]>([])
  const [bodyBatteryMetrics, setBodyBatteryMetrics] = useState<BodyBatteryMetric[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [error, setError] = useState('')
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncMessage, setSyncMessage] = useState('')

  useEffect(() => {
    checkGarminConnection()
  }, [])

  useEffect(() => {
    if (isGarminConnected) {
      fetchData()
    }
  }, [period, isGarminConnected])

  const handleSync = async () => {
    setIsSyncing(true)
    setSyncMessage('')
    try {
      await garminApi.triggerSync()
      setSyncMessage('Sync iniciado! Os dados serão atualizados em alguns minutos.')
      setTimeout(() => setSyncMessage(''), 5000)
    } catch {
      setSyncMessage('Erro ao iniciar sync.')
      setTimeout(() => setSyncMessage(''), 3000)
    } finally {
      setIsSyncing(false)
    }
  }

  const checkGarminConnection = async () => {
    try {
      const response = await garminApi.getStatus()
      setIsGarminConnected(response.data.is_connected)
      if (!response.data.is_connected) {
        setIsLoading(false)
      }
    } catch {
      setIsGarminConnected(false)
      setIsLoading(false)
    }
  }

  const fetchData = async () => {
    setIsLoading(true)
    setError('')

    const days = period === 'day' ? 0 : period === 'week' ? 7 : period === 'month' ? 30 : 365
    const startDate = format(subDays(new Date(), days), 'yyyy-MM-dd')
    const endDate = format(new Date(), 'yyyy-MM-dd')

    try {
      const [metricsResponse, summaryResponse] = await Promise.all([
        healthApi.getMetrics(startDate, endDate),
        healthApi.getSummary(period),
      ])

      const metrics = metricsResponse.data

      // Process daily metrics for activity chart
      const dailyData: DailyMetric[] = metrics.daily_stats?.map((d: { date: string; steps?: number; calories?: number; distance?: number }) => ({
        date: format(new Date(d.date), 'MMM d'),
        steps: d.steps || 0,
        calories: d.calories || 0,
        distance: d.distance || 0,
      })) || []

      // Process heart rate metrics
      const hrData: HeartRateMetric[] = metrics.heart_rate?.map((d: { date: string; resting?: number; avg?: number; max?: number }) => ({
        date: format(new Date(d.date), 'MMM d'),
        resting: d.resting || 0,
        avg: d.avg || 0,
        max: d.max || 0,
      })) || []

      // Process sleep metrics (convert seconds to minutes)
      const sleepData: SleepMetric[] = metrics.sleep?.map((d: { date: string; deep?: number; light?: number; rem?: number; awake?: number; duration?: number }) => ({
        date: format(new Date(d.date), 'MMM d'),
        deep: Math.round((d.deep || 0) / 60),
        light: Math.round((d.light || 0) / 60),
        rem: Math.round((d.rem || 0) / 60),
        awake: Math.round((d.awake || 0) / 60),
        total: Math.round((d.duration || 0) / 60),
      })) || []

      const bbData: BodyBatteryMetric[] = metrics.body_battery?.map((d: { date: string; max?: number; min?: number; end?: number }) => ({
        date: format(new Date(d.date), 'MMM d'),
        max: Math.round(d.max || 0),
        min: Math.round(d.min || 0),
        end: Math.round(d.end || 0),
      })) || []

      setDailyMetrics(dailyData)
      setHeartRateMetrics(hrData)
      setSleepMetrics(sleepData)
      setBodyBatteryMetrics(bbData)
      setSummary(summaryResponse.data)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string | Array<{ msg: string }> } } }
      const detail = error.response?.data?.detail

      if (typeof detail === 'string') {
        setError(detail)
      } else if (Array.isArray(detail) && detail.length > 0) {
        setError(detail[0].msg || 'Validation error')
      } else {
        setError('Failed to load health data')
      }
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading && isGarminConnected === null) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (!isGarminConnected) {
    return (
      <div className="max-w-2xl mx-auto">
        <Card>
          <CardContent className="py-12 text-center">
            <Watch className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Connect your Garmin account
            </h2>
            <p className="text-gray-600 mb-6">
              To view your health dashboard, you need to connect your Garmin
              Connect account first.
            </p>
            <Link href="/dashboard/settings">
              <Button>Go to Settings</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Dashboard</h1>
        <div className="flex gap-2 flex-wrap">
          {(['day', 'week', 'month', 'year'] as Period[]).map((p) => (
            <Button
              key={p}
              variant={period === p ? 'default' : 'outline'}
              size="sm"
              onClick={() => setPeriod(p)}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </Button>
          ))}
          <Button
            variant="outline"
            size="sm"
            onClick={handleSync}
            disabled={isSyncing}
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${isSyncing ? 'animate-spin' : ''}`} />
            {isSyncing ? 'Syncing...' : 'Sync'}
          </Button>
        </div>
      </div>
      {syncMessage && (
        <Alert>
          <AlertDescription>{syncMessage}</AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
            <MetricCard
              title="Avg Steps"
              value={summary?.avg_steps != null ? Math.round(summary.avg_steps).toLocaleString() : '—'}
              icon={<Footprints className="h-5 w-5" />}
              change={summary?.steps_change}
            />
            <MetricCard
              title="Avg Calories"
              value={summary?.avg_calories != null ? Math.round(summary.avg_calories).toLocaleString() : '—'}
              unit="kcal"
              icon={<Flame className="h-5 w-5" />}
              change={summary?.calories_change}
            />
            <MetricCard
              title="Resting Heart Rate"
              value={summary?.avg_resting_hr != null ? Math.round(summary.avg_resting_hr) : '—'}
              unit="bpm"
              icon={<Heart className="h-5 w-5" />}
            />
            <MetricCard
              title="Avg Sleep"
              value={summary?.avg_sleep_hours?.toFixed(1) || '—'}
              unit="hours"
              icon={<Moon className="h-5 w-5" />}
            />
          </div>

          {/* Activity Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Steps</CardTitle>
              </CardHeader>
              <CardContent>
                {dailyMetrics.length > 0 ? (
                  <ActivityChart data={dailyMetrics} metric="steps" />
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-gray-400">
                    No data available
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Calories Burned</CardTitle>
              </CardHeader>
              <CardContent>
                {dailyMetrics.length > 0 ? (
                  <ActivityChart data={dailyMetrics} metric="calories" />
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-gray-400">
                    No data available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Heart Rate Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Heart Rate</CardTitle>
            </CardHeader>
            <CardContent>
              {heartRateMetrics.length > 0 ? (
                <HeartRateChart data={heartRateMetrics} />
              ) : (
                <div className="h-[300px] flex items-center justify-center text-gray-400">
                  No data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Sleep Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Sleep Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              {sleepMetrics.length > 0 ? (
                <SleepChart data={sleepMetrics} />
              ) : (
                <div className="h-[300px] flex items-center justify-center text-gray-400">
                  No data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Body Battery Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Body Battery</CardTitle>
            </CardHeader>
            <CardContent>
              {bodyBatteryMetrics.length > 0 ? (
                <BodyBatteryChart data={bodyBatteryMetrics} />
              ) : (
                <div className="h-[300px] flex items-center justify-center text-gray-400">
                  No data available
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
