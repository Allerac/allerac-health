'use client'

import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Loader2 } from 'lucide-react'

export default function SSOPage() {
  const searchParams = useSearchParams()
  const router = useRouter()

  useEffect(() => {
    const token = searchParams.get('t')
    if (!token) {
      router.replace('/login')
      return
    }

    let cancelled = false

    fetch('/api/auth/sso', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
      .then((res) => {
        if (!res.ok) throw new Error('SSO failed')
        return res.json()
      })
      .then((data) => {
        if (cancelled) return
        localStorage.setItem('access_token', data.access_token)
        if (data.refresh_token) {
          localStorage.setItem('refresh_token', data.refresh_token)
        }
        router.replace('/dashboard')
      })
      .catch(() => {
        if (!cancelled) router.replace('/login?error=sso_failed')
      })

    return () => {
      cancelled = true
    }
  }, [searchParams, router])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-gray-500">
        <Loader2 className="h-8 w-8 animate-spin" />
        <p className="text-sm">Signing you in...</p>
      </div>
    </div>
  )
}
