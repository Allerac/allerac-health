'use client'

import { SessionProvider } from './session-provider'
import { QueryProvider } from './query-provider'
import { ThemeProvider } from './theme-provider'

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <SessionProvider>
        <QueryProvider>{children}</QueryProvider>
      </SessionProvider>
    </ThemeProvider>
  )
}
