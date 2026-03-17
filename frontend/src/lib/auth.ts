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
      },
      async authorize(credentials) {
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
    // Allerac One OIDC provider — enables SSO from chat.allerac.ai
    {
      id: 'allerac-one',
      name: 'Allerac One',
      type: 'oauth',
      wellKnown: `${process.env.ALLERAC_ONE_ISSUER}/.well-known/openid-configuration`,
      authorization: { params: { scope: 'openid email profile' } },
      clientId: process.env.ALLERAC_ONE_CLIENT_ID,
      clientSecret: process.env.ALLERAC_ONE_CLIENT_SECRET,
      idToken: true,
      checks: ['state'],
      profile(profile) {
        return {
          id: profile.sub,
          name: profile.name,
          email: profile.email,
        }
      },
    },
  ],
  callbacks: {
    async jwt({ token, user, account }) {
      // Allerac One OIDC sign-in: exchange the OIDC id_token for backend local tokens.
      if (account?.provider === 'allerac-one' && account.id_token) {
        try {
          const response = await axios.post(`${API_URL}/api/v1/auth/allerac-one`, {
            id_token: account.id_token,
          })
          const { access_token, refresh_token, user: backendUser } = response.data
          token.id = backendUser.id
          token.accessToken = access_token
          token.refreshToken = refresh_token
        } catch {
          // token exchange failed — session will have no accessToken
        }
      }
      // Credentials sign-in
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
