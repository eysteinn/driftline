import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'

// Pages
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import MissionsPage from './pages/MissionsPage'
import NewMissionPage from './pages/NewMissionPage'
import MissionDetailsPage from './pages/MissionDetailsPage'
import ResultsPage from './pages/ResultsPage'
import ProfilePage from './pages/ProfilePage'
import ApiKeysPage from './pages/ApiKeysPage'

// Components
import PrivateRoute from './components/PrivateRoute'

const queryClient = new QueryClient()

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            
            {/* Protected Routes */}
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <DashboardPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/missions"
              element={
                <PrivateRoute>
                  <MissionsPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/missions/new"
              element={
                <PrivateRoute>
                  <NewMissionPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/missions/:id"
              element={
                <PrivateRoute>
                  <MissionDetailsPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/missions/:id/results"
              element={
                <PrivateRoute>
                  <ResultsPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <PrivateRoute>
                  <ProfilePage />
                </PrivateRoute>
              }
            />
            <Route
              path="/api-keys"
              element={
                <PrivateRoute>
                  <ApiKeysPage />
                </PrivateRoute>
              }
            />
            
            {/* Catch all - redirect to dashboard */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App
