'use client'

/**
 * OIDC bridge page.
 *
 * After the allerac-one OAuth flow completes, NextAuth redirects here.
 * The NextAuth session contains the backend access_token and refresh_token
 * obtained by exchanging the OIDC id_token server-side.
 * This page copies them into localStorage (where the API client reads them)
 * and then redirects to the dashboard.
 */

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { Loader2 } from 'lucide-react'

export default function AuthBridgePage() {
  const { data: session, status } = useSession()
  const router = useRouter()

  useEffect(() => {
    if (status === 'loading') return

    if (status === 'authenticated' && session?.accessToken) {
      localStorage.setItem('access_token', session.accessToken)
      if (session.refreshToken) {
        localStorage.setItem('refresh_token', session.refreshToken)
      }
      router.replace('/dashboard')
      return
    }

    // Not authenticated or token exchange failed → back to login
    router.replace('/login')
  }, [session, status, router])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-gray-500">
        <Loader2 className="h-8 w-8 animate-spin" />
        <p className="text-sm">Signing you in...</p>
      </div>
    </div>
  )
}
