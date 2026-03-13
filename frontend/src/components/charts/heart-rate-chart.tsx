'use client'

import { useChartTheme } from '@/lib/use-chart-theme'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface HeartRateChartProps {
  data: Array<{
    date: string
    resting: number
    avg: number
    max: number
  }>
}

export function HeartRateChart({ data }: HeartRateChartProps) {
  const { tooltipStyle, gridColor, textColor } = useChartTheme()

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
        <XAxis dataKey="date" tick={{ fontSize: 12, fill: textColor }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 12, fill: textColor }} tickLine={false} axisLine={false} domain={['dataMin - 10', 'dataMax + 10']} />
        <Tooltip contentStyle={tooltipStyle}
          formatter={(value: number, name: string) => {
            const labels: Record<string, string> = {
              resting: 'Resting',
              avg: 'Average',
              max: 'Max',
            }
            return [`${value} bpm`, labels[name] || name]
          }}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="resting"
          stroke="#ef4444"
          strokeWidth={2}
          dot={false}
          name="Resting"
        />
        <Line
          type="monotone"
          dataKey="avg"
          stroke="#f97316"
          strokeWidth={2}
          dot={false}
          name="Average"
        />
        <Line
          type="monotone"
          dataKey="max"
          stroke="#eab308"
          strokeWidth={2}
          dot={false}
          name="Max"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
