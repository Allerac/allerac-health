import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor para adicionar token
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// Interceptor para refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          })

          const { access_token, refresh_token } = response.data
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', refresh_token)

          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        }
      } catch {
        // Refresh falhou - logout
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  register: (data: { email: string; password: string; name?: string }) =>
    api.post('/api/v1/auth/register', data),

  login: (data: { email: string; password: string }) =>
    api.post('/api/v1/auth/login', data),

  refresh: (refreshToken: string) =>
    api.post('/api/v1/auth/refresh', { refresh_token: refreshToken }),
}

// User API
export const userApi = {
  getMe: () => api.get('/api/v1/users/me'),
  updateMe: (data: { name?: string }) => api.put('/api/v1/users/me', data),
  deleteMe: () => api.delete('/api/v1/users/me'),
}

// Garmin API
export const garminApi = {
  getStatus: () => api.get('/api/v1/garmin/status'),

  connect: (data: { email: string; password: string }) =>
    api.post('/api/v1/garmin/connect', data),

  submitMfa: (data: { mfa_code: string }) =>
    api.post('/api/v1/garmin/mfa', data),

  disconnect: () => api.delete('/api/v1/garmin/disconnect'),

  triggerSync: () => api.post('/api/v1/garmin/sync'),
}

// Health API
export const healthApi = {
  getMetrics: (startDate?: string, endDate?: string) =>
    api.get('/api/v1/health/metrics', {
      params: { start_date: startDate, end_date: endDate },
    }),

  getDailyMetrics: (date: string) =>
    api.get(`/api/v1/health/daily/${date}`),

  getSummary: (period: 'day' | 'week' | 'month' | 'year' = 'week') =>
    api.get('/api/v1/health/summary', { params: { period } }),
}
