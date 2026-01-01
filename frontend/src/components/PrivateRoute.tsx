import { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

interface PrivateRouteProps {
  children: ReactNode
}

export default function PrivateRoute({ children }: PrivateRouteProps) {
  const { isAuthenticated, accessToken } = useAuthStore()

  if (!isAuthenticated || !accessToken) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
