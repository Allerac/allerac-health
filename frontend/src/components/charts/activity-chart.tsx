'use client'

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface ActivityChartProps {
  data: Array<{
    date: string
    steps: number
    calories: number
  }>
  metric: 'steps' | 'calories'
}

export function ActivityChart({ data, metric }: ActivityChartProps) {
  const color = metric === 'steps' ? '#3b82f6' : '#f97316'
  const label = metric === 'steps' ? 'Steps' : 'Calories'

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={`color${metric}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
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
          tickFormatter={(value) =>
            metric === 'steps' ? `${(value / 1000).toFixed(0)}k` : value.toString()
          }
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
          }}
          formatter={(value: number) => [value.toLocaleString(), label]}
        />
        <Area
          type="monotone"
          dataKey={metric}
          stroke={color}
          strokeWidth={2}
          fillOpacity={1}
          fill={`url(#color${metric})`}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
