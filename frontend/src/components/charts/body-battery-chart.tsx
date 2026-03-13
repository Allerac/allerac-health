'use client'

import { useChartTheme } from '@/lib/use-chart-theme'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'

interface BodyBatteryChartProps {
  data: Array<{
    date: string
    max: number
    min: number
    end: number
  }>
}

export function BodyBatteryChart({ data }: BodyBatteryChartProps) {
  const { tooltipStyle, gridColor, textColor } = useChartTheme()

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="bbGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0.05} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
        <XAxis dataKey="date" tick={{ fontSize: 12, fill: textColor }} tickLine={false} axisLine={false} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: textColor }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} />
        <Tooltip contentStyle={tooltipStyle}
          formatter={(value: number, name: string) => {
            const labels: Record<string, string> = {
              max: 'Máximo',
              min: 'Mínimo',
              end: 'Fim do dia',
            }
            return [`${Math.round(value)}%`, labels[name] || name]
          }}
        />
        <ReferenceLine y={25} stroke="#f97316" strokeDasharray="4 4" label={{ value: 'Baixo', fontSize: 10, fill: '#f97316' }} />
        <Area
          type="monotone"
          dataKey="max"
          stroke="#22c55e"
          strokeWidth={2}
          fill="url(#bbGradient)"
          name="max"
          dot={false}
        />
        <Area
          type="monotone"
          dataKey="end"
          stroke="#3b82f6"
          strokeWidth={2}
          fill="none"
          name="end"
          dot={{ r: 3, fill: '#3b82f6' }}
          strokeDasharray="5 3"
        />
        <Area
          type="monotone"
          dataKey="min"
          stroke="#f97316"
          strokeWidth={1.5}
          fill="none"
          name="min"
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
