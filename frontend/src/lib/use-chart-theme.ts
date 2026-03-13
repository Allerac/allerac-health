'use client'

import { useTheme } from 'next-themes'

export function useChartTheme() {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'

  return {
    tooltipStyle: {
      backgroundColor: isDark ? '#1f2937' : 'white',
      border: `1px solid ${isDark ? '#374151' : '#e5e7eb'}`,
      borderRadius: '8px',
      color: isDark ? '#f9fafb' : '#111827',
    },
    gridColor: isDark ? '#374151' : '#e5e7eb',
    textColor: isDark ? '#9ca3af' : '#6b7280',
  }
}
