import axios, { AxiosInstance, AxiosError } from 'axios'
import type { 
  User, 
  LoginRequest, 
  RegisterRequest, 
  AuthTokens, 
  Mission,
  CreateMissionRequest,
  MissionResult,
  ApiResponse,
  PaginatedResponse,
  ApiKey,
  Subscription,
  UsageRecord
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('accessToken')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for error handling and token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config

        // If 401 and we have a refresh token, try to refresh
        if (error.response?.status === 401 && originalRequest && !originalRequest.headers._retry) {
          originalRequest.headers._retry = 'true'
          
          const refreshToken = localStorage.getItem('refreshToken')
          if (refreshToken) {
            try {
              const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
                refreshToken,
              })
              const { accessToken } = response.data
              localStorage.setItem('accessToken', accessToken)
              
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${accessToken}`
              }
              return this.client(originalRequest)
            } catch (refreshError) {
              // Refresh failed, logout
              localStorage.removeItem('accessToken')
              localStorage.removeItem('refreshToken')
              window.location.href = '/login'
              return Promise.reject(refreshError)
            }
          }
        }
        
        return Promise.reject(error)
      }
    )
  }

  // Auth endpoints
  async login(data: LoginRequest): Promise<AuthTokens & { user: User }> {
    const response = await this.client.post<ApiResponse<AuthTokens & { user: User }>>('/auth/login', data)
    return response.data.data
  }

  async register(data: RegisterRequest): Promise<AuthTokens & { user: User }> {
    const response = await this.client.post<ApiResponse<AuthTokens & { user: User }>>('/auth/register', data)
    return response.data.data
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout')
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<ApiResponse<User>>('/users/me')
    return response.data.data
  }

  async updateCurrentUser(data: Partial<User>): Promise<User> {
    const response = await this.client.patch<ApiResponse<User>>('/users/me', data)
    return response.data.data
  }

  // Mission endpoints
  async createMission(data: CreateMissionRequest): Promise<Mission> {
    const response = await this.client.post<ApiResponse<Mission>>('/missions', data)
    return response.data.data
  }

  async getMissions(params?: { page?: number; perPage?: number }): Promise<PaginatedResponse<Mission>> {
    const response = await this.client.get<PaginatedResponse<Mission>>('/missions', { params })
    return response.data
  }

  async getMission(id: string): Promise<Mission> {
    const response = await this.client.get<ApiResponse<Mission>>(`/missions/${id}`)
    return response.data.data
  }

  async deleteMission(id: string): Promise<void> {
    await this.client.delete(`/missions/${id}`)
  }

  async getMissionStatus(id: string): Promise<{ status: string; progress?: number }> {
    const response = await this.client.get<ApiResponse<{ status: string; progress?: number }>>(`/missions/${id}/status`)
    return response.data.data
  }

  async getMissionResults(id: string): Promise<MissionResult> {
    const response = await this.client.get<ApiResponse<MissionResult>>(`/missions/${id}/results`)
    return response.data.data
  }

  async downloadMissionResults(id: string, format: 'netcdf' | 'geojson' | 'pdf'): Promise<Blob> {
    const response = await this.client.get(`/missions/${id}/results/download`, {
      params: { format },
      responseType: 'blob',
    })
    return response.data
  }

  // API Key endpoints
  async getApiKeys(): Promise<ApiKey[]> {
    const response = await this.client.get<ApiResponse<ApiKey[]>>('/users/me/api-keys')
    return response.data.data
  }

  async createApiKey(name: string, scopes?: string[]): Promise<{ key: string; apiKey: ApiKey }> {
    const response = await this.client.post<ApiResponse<{ key: string; apiKey: ApiKey }>>('/users/me/api-keys', {
      name,
      scopes,
    })
    return response.data.data
  }

  async deleteApiKey(id: string): Promise<void> {
    await this.client.delete(`/users/me/api-keys/${id}`)
  }

  // Billing endpoints
  async getSubscription(): Promise<Subscription | null> {
    const response = await this.client.get<ApiResponse<Subscription | null>>('/billing/subscription')
    return response.data.data
  }

  async getUsage(params?: { startDate?: string; endDate?: string }): Promise<UsageRecord[]> {
    const response = await this.client.get<ApiResponse<UsageRecord[]>>('/billing/usage', { params })
    return response.data.data
  }

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get('/health')
    return response.data
  }
}

export const apiClient = new ApiClient()
export default apiClient
