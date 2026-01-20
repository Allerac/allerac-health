import 'next-auth'

declare module 'next-auth' {
  interface User {
    id: string
    accessToken: string
    refreshToken: string
  }

  interface Session {
    user: {
      id: string
      email: string
      name?: string | null
    }
    accessToken: string
    refreshToken: string
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    id: string
    accessToken: string
    refreshToken: string
  }
}
