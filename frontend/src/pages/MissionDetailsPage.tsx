import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Container,
  Paper,
  Typography,
  Box,
  Grid,
  Chip,
  Button,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Divider,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  Map as MapIcon,
} from '@mui/icons-material'
import Layout from '../components/Layout'
import { useMissionStore } from '../stores/missionStore'
import { apiClient } from '../services/api'

export default function MissionDetailsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { currentMission, fetchMission, isLoading, error } = useMissionStore()
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (id) {
      fetchMission(id)
    }
  }, [id, fetchMission])

  const handleRefresh = async () => {
    if (id) {
      setRefreshing(true)
      await fetchMission(id)
      setRefreshing(false)
    }
  }

  const handleDownload = async (format: 'netcdf' | 'geojson' | 'pdf') => {
    if (!id) return
    
    try {
      const blob = await apiClient.downloadMissionResults(id, format)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `mission-${id}-results.${format === 'netcdf' ? 'nc' : format === 'geojson' ? 'json' : 'pdf'}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Download failed:', error)
    }
  }

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

  if (isLoading && !currentMission) {
    return (
      <Layout>
        <Container maxWidth="lg">
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        </Container>
      </Layout>
    )
  }

  if (error || !currentMission) {
    return (
      <Layout>
        <Container maxWidth="lg">
          <Alert severity="error">{error || 'Mission not found'}</Alert>
          <Button onClick={() => navigate('/missions')} sx={{ mt: 2 }}>
            Back to Missions
          </Button>
        </Container>
      </Layout>
    )
  }

  return (
    <Layout>
      <Container maxWidth="lg">
        <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h4">{currentMission.name}</Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="outlined"
              startIcon={refreshing ? <CircularProgress size={20} /> : <RefreshIcon />}
              onClick={handleRefresh}
              disabled={refreshing}
            >
              Refresh
            </Button>
            {currentMission.status === 'completed' && (
              <Button
                variant="contained"
                startIcon={<MapIcon />}
                onClick={() => navigate(`/missions/${id}/results`)}
              >
                View Results
              </Button>
            )}
          </Box>
        </Box>

        <Grid container spacing={3}>
          {/* Status Card */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Status
                </Typography>
                <Chip
                  label={currentMission.status}
                  color={getStatusColor(currentMission.status) as any}
                  sx={{ mt: 1 }}
                />
                {currentMission.status === 'processing' && (
                  <Box sx={{ mt: 2 }}>
                    <CircularProgress size={40} />
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Processing simulation...
                    </Typography>
                  </Box>
                )}
                {currentMission.status === 'failed' && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    Mission failed. Please try again.
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Mission Info */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Mission Information
              </Typography>
              <Divider sx={{ my: 2 }} />
              
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Object Type
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {currentMission.objectType}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Forecast Hours
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {currentMission.forecastHours}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Ensemble Size
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {currentMission.ensembleSize} particles
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Uncertainty Radius
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {currentMission.uncertaintyRadiusM || 0} m
                  </Typography>
                </Grid>
              </Grid>

              <Divider sx={{ my: 2 }} />

              <Typography variant="h6" gutterBottom>
                Position & Time
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Latitude
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {currentMission.lastKnownLat.toFixed(6)}°
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Longitude
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {currentMission.lastKnownLon.toFixed(6)}°
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary">
                    Last Known Time
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {new Date(currentMission.lastKnownTime).toLocaleString()}
                  </Typography>
                </Grid>
              </Grid>

              {currentMission.description && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="h6" gutterBottom>
                    Description
                  </Typography>
                  <Typography variant="body1">
                    {currentMission.description}
                  </Typography>
                </>
              )}

              <Divider sx={{ my: 2 }} />
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Created
                  </Typography>
                  <Typography variant="body1">
                    {new Date(currentMission.createdAt).toLocaleString()}
                  </Typography>
                </Grid>
                {currentMission.completedAt && (
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Completed
                    </Typography>
                    <Typography variant="body1">
                      {new Date(currentMission.completedAt).toLocaleString()}
                    </Typography>
                  </Grid>
                )}
              </Grid>
            </Paper>
          </Grid>

          {/* Download Options */}
          {currentMission.status === 'completed' && (
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Download Results
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                  <Button
                    variant="outlined"
                    startIcon={<DownloadIcon />}
                    onClick={() => handleDownload('geojson')}
                  >
                    GeoJSON
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<DownloadIcon />}
                    onClick={() => handleDownload('netcdf')}
                  >
                    NetCDF
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<DownloadIcon />}
                    onClick={() => handleDownload('pdf')}
                  >
                    PDF Report
                  </Button>
                </Box>
              </Paper>
            </Grid>
          )}
        </Grid>
      </Container>
    </Layout>
  )
}
