'use client'

import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: string | number
  unit?: string
  icon: React.ReactNode
  change?: number
  className?: string
}

export function MetricCard({
  title,
  value,
  unit,
  icon,
  change,
  className,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        'bg-white rounded-xl border p-6 shadow-sm',
        className
      )}
    >
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-medium text-gray-500">{title}</span>
        <div className="text-gray-400">{icon}</div>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-bold text-gray-900">{value}</span>
        {unit && <span className="text-sm text-gray-500">{unit}</span>}
      </div>
      {change !== undefined && (
        <div className="mt-2">
          <span
            className={cn(
              'text-sm font-medium',
              change >= 0 ? 'text-green-600' : 'text-red-600'
            )}
          >
            {change >= 0 ? '+' : ''}
            {change}%
          </span>
          <span className="text-sm text-gray-500 ml-1">vs last week</span>
        </div>
      )}
    </div>
  )
}
