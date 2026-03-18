import { NextAuthOptions } from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'
import axios from 'axios'

// NEXT_PUBLIC_API_URL works in the browser but NOT server-side inside Docker
// (localhost resolves to the frontend container itself, not the backend).
// INTERNAL_API_URL is the Docker-internal hostname used for server-side calls.
const API_URL = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
        ssoToken: { label: 'SSO Token', type: 'text' },
      },
      async authorize(credentials) {
        // SSO flow: short-lived token from allerac-one
        if (credentials?.ssoToken) {
          try {
            const response = await axios.post(`${API_URL}/api/v1/auth/sso`, {
              token: credentials.ssoToken,
            })
            const { access_token, refresh_token, user } = response.data
            return {
              id: user.id,
              email: user.email,
              name: user.name,
              accessToken: access_token,
              refreshToken: refresh_token,
            }
          } catch {
            return null
          }
        }

        if (!credentials?.email || !credentials?.password) {
          return null
        }

        try {
          const response = await axios.post(`${API_URL}/api/v1/auth/login`, {
            email: credentials.email,
            password: credentials.password,
          })

          const { access_token, refresh_token, user } = response.data

          return {
            id: user.id,
            email: user.email,
            name: user.name,
            accessToken: access_token,
            refreshToken: refresh_token,
          }
        } catch {
          return null
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id
        token.accessToken = (user as Record<string, unknown>).accessToken as string
        token.refreshToken = (user as Record<string, unknown>).refreshToken as string
      }
      return token
    },
    async session({ session, token }) {
      session.user.id = token.id as string
      session.accessToken = token.accessToken as string
      session.refreshToken = token.refreshToken as string
      return session
    },
  },
  pages: {
    signIn: '/login',
    error: '/login',
  },
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
}
