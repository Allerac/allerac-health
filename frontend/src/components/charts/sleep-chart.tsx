'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface SleepChartProps {
  data: Array<{
    date: string
    deep: number
    light: number
    rem: number
    awake: number
  }>
}

export function SleepChart({ data }: SleepChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(value) => `${(value / 60).toFixed(0)}h`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
          }}
          formatter={(value: number, name: string) => {
            const hours = Math.floor(value / 60)
            const minutes = value % 60
            const labels: Record<string, string> = {
              deep: 'Deep',
              light: 'Light',
              rem: 'REM',
              awake: 'Awake',
            }
            return [`${hours}h ${minutes}m`, labels[name] || name]
          }}
        />
        <Legend />
        <Bar dataKey="deep" stackId="sleep" fill="#6366f1" name="Deep" />
        <Bar dataKey="light" stackId="sleep" fill="#a5b4fc" name="Light" />
        <Bar dataKey="rem" stackId="sleep" fill="#818cf8" name="REM" />
        <Bar dataKey="awake" stackId="sleep" fill="#fca5a5" name="Awake" />
      </BarChart>
    </ResponsiveContainer>
  )
}
