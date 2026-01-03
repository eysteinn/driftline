import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '../types'
import { apiClient } from '../services/api'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => void
  fetchCurrentUser: () => Promise<void>
  clearError: () => void
}

// Helper function to store tokens
const storeTokens = (accessToken: string, refreshToken: string) => {
  localStorage.setItem('accessToken', accessToken)
  localStorage.setItem('refreshToken', refreshToken)
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await apiClient.login({ email, password })
          
          // Store tokens using helper
          storeTokens(response.accessToken, response.refreshToken)
          
          set({
            user: response.user,
            accessToken: response.accessToken,
            refreshToken: response.refreshToken,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error: any) {
          set({
            error: error.response?.data?.message || 'Login failed',
            isLoading: false,
          })
          throw error
        }
      },

      register: async (email: string, password: string, fullName: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await apiClient.register({ email, password, fullName })
          
          // Store tokens using helper
          storeTokens(response.accessToken, response.refreshToken)
          
          set({
            user: response.user,
            accessToken: response.accessToken,
            refreshToken: response.refreshToken,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error: any) {
          set({
            error: error.response?.data?.message || 'Registration failed',
            isLoading: false,
          })
          throw error
        }
      },

      logout: () => {
        apiClient.logout().catch(console.error)
        localStorage.removeItem('accessToken')
        localStorage.removeItem('refreshToken')
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })
      },

      fetchCurrentUser: async () => {
        if (!get().accessToken) return
        
        set({ isLoading: true })
        try {
          const user = await apiClient.getCurrentUser()
          set({ user, isAuthenticated: true, isLoading: false })
        } catch (error) {
          set({ isLoading: false })
          // Don't throw, just fail silently
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
      onRehydrateStorage: () => (state) => {
        // Set isAuthenticated based on token presence during rehydration
        if (state) {
          state.isAuthenticated = !!state.accessToken
        }
      },
    }
  )
)
