'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Activity, LayoutDashboard, Settings, LogOut } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings },
]

export function DashboardNav() {
  const pathname = usePathname()

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    window.location.href = '/'
  }

  return (
    <>
      {/* Sidebar — desktop */}
      <aside className="hidden md:flex w-64 bg-white dark:bg-gray-900 border-r dark:border-gray-800 min-h-screen p-4 flex-col">
        <Link href="/dashboard" className="flex items-center gap-2 mb-8 px-2">
          <Activity className="h-8 w-8 text-blue-600" />
          <span className="text-xl font-bold text-gray-900 dark:text-gray-100">Allerac Health</span>
        </Link>

        <nav className="flex-1 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-50 dark:bg-blue-950 text-blue-600'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100'
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </Link>
            )
          })}
        </nav>

        <Button
          variant="ghost"
          className="justify-start gap-3 text-gray-600 hover:text-gray-900"
          onClick={handleLogout}
        >
          <LogOut className="h-5 w-5" />
          Sign Out
        </Button>
      </aside>

      {/* Bottom nav — mobile */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-gray-900 border-t dark:border-gray-800 flex items-center justify-around px-2 h-16">
        {navItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex flex-col items-center gap-1 px-4 py-2 rounded-lg text-xs font-medium transition-colors',
                isActive ? 'text-blue-600' : 'text-gray-500'
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.label}
            </Link>
          )
        })}
        <button
          onClick={handleLogout}
          className="flex flex-col items-center gap-1 px-4 py-2 rounded-lg text-xs font-medium text-gray-500"
        >
          <LogOut className="h-5 w-5" />
          Sign Out
        </button>
      </nav>
    </>
  )
}
