'use client'

import { useState, useEffect } from 'react'
import { useTheme } from 'next-themes'
import { Watch, Loader2, CheckCircle, XCircle, AlertCircle, Sun, Moon, Monitor } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { garminApi } from '@/lib/api'

type GarminStatus = {
  is_connected: boolean
  mfa_pending?: boolean
  email?: string
  last_sync_at?: string
  last_error?: string
  message?: string
}

type ConnectionState = 'idle' | 'connecting' | 'mfa_required' | 'connected' | 'error'

export default function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const [garminStatus, setGarminStatus] = useState<GarminStatus | null>(null)
  const [connectionState, setConnectionState] = useState<ConnectionState>('idle')
  const [garminEmail, setGarminEmail] = useState('')
  const [garminPassword, setGarminPassword] = useState('')
  const [mfaCode, setMfaCode] = useState('')
  const [mfaMessage, setMfaMessage] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    fetchGarminStatus()
  }, [])

  const fetchGarminStatus = async () => {
    try {
      const response = await garminApi.getStatus()
      setGarminStatus(response.data)
      if (response.data.is_connected) {
        setConnectionState('connected')
      }
    } catch {
      // Not connected yet
    } finally {
      setIsLoading(false)
    }
  }

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setConnectionState('connecting')

    try {
      const response = await garminApi.connect({
        email: garminEmail,
        password: garminPassword,
      })

      if (response.data.mfa_pending) {
        setMfaMessage(response.data.message || 'Please check your email or phone for the MFA code.')
        setConnectionState('mfa_required')
      } else if (response.data.is_connected) {
        setConnectionState('connected')
        setGarminEmail('')
        setGarminPassword('')
        fetchGarminStatus()
      } else {
        // Unknown state - refresh status
        fetchGarminStatus()
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string | Array<{ msg: string }> } } }
      const detail = error.response?.data?.detail

      if (typeof detail === 'string') {
        setError(detail)
      } else if (Array.isArray(detail) && detail.length > 0) {
        setError(detail[0].msg || 'Validation error')
      } else {
        setError('Failed to connect to Garmin')
      }
      setConnectionState('error')
    }
  }

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setConnectionState('connecting')

    try {
      const response = await garminApi.submitMfa({ mfa_code: mfaCode })

      if (response.data.is_connected) {
        setConnectionState('connected')
        setGarminEmail('')
        setGarminPassword('')
        setMfaCode('')
        fetchGarminStatus()
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string | Array<{ msg: string }> } } }
      const detail = error.response?.data?.detail

      if (typeof detail === 'string') {
        setError(detail)
      } else if (Array.isArray(detail) && detail.length > 0) {
        setError(detail[0].msg || 'Validation error')
      } else {
        setError('Invalid MFA code')
      }
      setConnectionState('mfa_required')
    }
  }

  const handleDisconnect = async () => {
    try {
      await garminApi.disconnect()
      setGarminStatus(null)
      setConnectionState('idle')
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string | Array<{ msg: string }> } } }
      const detail = error.response?.data?.detail

      if (typeof detail === 'string') {
        setError(detail)
      } else if (Array.isArray(detail) && detail.length > 0) {
        setError(detail[0].msg || 'Validation error')
      } else {
        setError('Failed to disconnect')
      }
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Settings</h1>

      {/* Theme */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <Sun className="h-6 w-6 text-yellow-500" />
            <div>
              <CardTitle>Appearance</CardTitle>
              <CardDescription>Choose your preferred theme</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            {[
              { value: 'light', label: 'Light', icon: Sun },
              { value: 'dark', label: 'Dark', icon: Moon },
              { value: 'system', label: 'System', icon: Monitor },
            ].map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                onClick={() => setTheme(value)}
                className={`flex flex-1 flex-col items-center gap-2 rounded-lg border-2 p-4 transition-colors ${
                  theme === value
                    ? 'border-blue-600 bg-blue-50 dark:bg-blue-950'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className={`h-5 w-5 ${theme === value ? 'text-blue-600' : 'text-gray-500'}`} />
                <span className={`text-sm font-medium ${theme === value ? 'text-blue-600' : 'text-gray-600 dark:text-gray-400'}`}>
                  {label}
                </span>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <Watch className="h-6 w-6 text-orange-500" />
            <div>
              <CardTitle>Garmin Connect</CardTitle>
              <CardDescription>
                Connect your Garmin account to sync your health data
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {connectionState === 'connected' && garminStatus?.is_connected ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="h-5 w-5" />
                <span className="font-medium">Connected</span>
              </div>
              {garminStatus.email && (
                <p className="text-sm text-gray-600">
                  Account: {garminStatus.email}
                </p>
              )}
              {garminStatus.last_sync_at && (
                <p className="text-sm text-gray-600">
                  Last synced: {new Date(garminStatus.last_sync_at).toLocaleString()}
                </p>
              )}
              {garminStatus.last_error && (
                <Alert variant="warning" className="mt-2">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Last sync error: {garminStatus.last_error}
                  </AlertDescription>
                </Alert>
              )}
              <Button variant="destructive" onClick={handleDisconnect}>
                Disconnect Garmin
              </Button>
            </div>
          ) : connectionState === 'mfa_required' ? (
            <form onSubmit={handleMfaSubmit} className="space-y-4">
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {mfaMessage || 'Garmin requires multi-factor authentication. Please enter the code sent to your email or phone.'}
                </AlertDescription>
              </Alert>
              <div className="space-y-2">
                <Label htmlFor="mfaCode">MFA Code</Label>
                <Input
                  id="mfaCode"
                  type="text"
                  placeholder="Enter 6-digit code"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  required
                  maxLength={6}
                  className="text-center text-2xl tracking-widest"
                />
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={connectionState === 'connecting'}>
                  {connectionState === 'connecting' ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    'Verify Code'
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setConnectionState('idle')
                    setMfaCode('')
                    setMfaMessage('')
                    setError('')
                  }}
                >
                  Cancel
                </Button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleConnect} className="space-y-4">
              {connectionState === 'error' && (
                <div className="flex items-center gap-2 text-red-600 mb-2">
                  <XCircle className="h-5 w-5" />
                  <span className="font-medium">Connection failed</span>
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="garminEmail">Garmin Email</Label>
                <Input
                  id="garminEmail"
                  type="email"
                  placeholder="your-garmin@email.com"
                  value={garminEmail}
                  onChange={(e) => setGarminEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="garminPassword">Garmin Password</Label>
                <Input
                  id="garminPassword"
                  type="password"
                  placeholder="Your Garmin password"
                  value={garminPassword}
                  onChange={(e) => setGarminPassword(e.target.value)}
                  required
                />
              </div>
              <p className="text-xs text-gray-500">
                Your credentials are encrypted and stored securely. We use them only
                to fetch your health data from Garmin Connect.
              </p>
              <Button type="submit" disabled={connectionState === 'connecting'}>
                {connectionState === 'connecting' ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  'Connect Garmin'
                )}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
