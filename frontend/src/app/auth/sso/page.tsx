'use client'

/**
 * SSO landing page for allerac-one sign-in.
 *
 * allerac-one redirects here with a short-lived HS256 token:
 *   https://health.allerac.ai/auth/sso?t=<token>
 *
 * This page exchanges the token for a NextAuth session and then hands off
 * to /auth/bridge, which stores the tokens in localStorage and goes to /dashboard.
 */

import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { signIn } from 'next-auth/react'
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

    signIn('credentials', { ssoToken: token, redirect: false }).then((result) => {
      if (result?.ok) {
        router.replace('/auth/bridge')
      } else {
        router.replace('/login?error=sso_failed')
      }
    })
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
