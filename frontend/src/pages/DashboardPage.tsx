import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Button,
  Card,
  CardContent,
  CardActions,
  Chip,
} from '@mui/material'
import {
  Add as AddIcon,
  TrendingUp as TrendingUpIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material'
import { useMissionStore } from '../stores/missionStore'
import { useAuthStore } from '../stores/authStore'
import Layout from '../components/Layout'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { missions, fetchMissions } = useMissionStore()

  useEffect(() => {
    fetchMissions()
  }, [fetchMissions])

  const recentMissions = (missions || []).slice(0, 5)
  const completedCount = (missions || []).filter(m => m.status === 'completed').length
  const processingCount = (missions || []).filter(m => m.status === 'processing' || m.status === 'queued').length

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'processing':
        return 'info'
      case 'queued':
        return 'warning'
      case 'failed':
        return 'error'
      default:
        return 'default'
    }
  }

  return (
    <Layout>
      <Container maxWidth="lg">
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" gutterBottom>
            Welcome back, {user?.fullName || 'User'}!
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Monitor your SAR drift forecasting missions
          </Typography>
        </Box>

        {/* Stats Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <TrendingUpIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Total Missions</Typography>
              </Box>
              <Typography variant="h3">{missions.length}</Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="h6">Completed</Typography>
              </Box>
              <Typography variant="h3">{completedCount}</Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <ScheduleIcon color="info" sx={{ mr: 1 }} />
                <Typography variant="h6">In Progress</Typography>
              </Box>
              <Typography variant="h3">{processingCount}</Typography>
            </Paper>
          </Grid>
        </Grid>

        {/* Quick Actions */}
        <Box sx={{ mb: 4 }}>
          <Button
            variant="contained"
            size="large"
            startIcon={<AddIcon />}
            onClick={() => navigate('/missions/new')}
          >
            Create New Mission
          </Button>
        </Box>

        {/* Recent Missions */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Recent Missions
          </Typography>
          
          {recentMissions.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography color="text.secondary">
                No missions yet. Create your first mission to get started!
              </Typography>
            </Box>
          ) : (
            <Grid container spacing={2}>
              {recentMissions.map((mission) => (
                <Grid item xs={12} key={mission.id}>
                  <Card>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 1 }}>
                        <Typography variant="h6">{mission.name}</Typography>
                        <Chip
                          label={mission.status}
                          color={getStatusColor(mission.status) as any}
                          size="small"
                        />
                      </Box>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        {mission.description || 'No description'}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                        <Typography variant="body2">
                          <strong>Object:</strong> {mission.objectType}
                        </Typography>
                        <Typography variant="body2">
                          <strong>Forecast:</strong> {mission.forecastHours}h
                        </Typography>
                        <Typography variant="body2">
                          <strong>Created:</strong> {new Date(mission.createdAt).toLocaleDateString()}
                        </Typography>
                      </Box>
                    </CardContent>
                    <CardActions>
                      <Button size="small" onClick={() => navigate(`/missions/${mission.id}`)}>
                        View Details
                      </Button>
                      {mission.status === 'completed' && (
                        <Button size="small" onClick={() => navigate(`/missions/${mission.id}/results`)}>
                          View Results
                        </Button>
                      )}
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
          
          {missions.length > 5 && (
            <Box sx={{ mt: 2, textAlign: 'center' }}>
              <Button onClick={() => navigate('/missions')}>
                View All Missions
              </Button>
            </Box>
          )}
        </Paper>
      </Container>
    </Layout>
  )
}
