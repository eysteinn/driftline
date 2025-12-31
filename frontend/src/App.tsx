import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'

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
            <Route path="/" element={
              <div style={{ padding: '20px', textAlign: 'center' }}>
                <h1>Driftline</h1>
                <p>Global SAR Drift Forecasting Platform</p>
                <p>Frontend is ready for development</p>
              </div>
            } />
          </Routes>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App
