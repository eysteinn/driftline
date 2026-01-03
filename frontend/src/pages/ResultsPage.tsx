import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Container,
  Paper,
  Typography,
  Box,
  Grid,
  Button,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  ToggleButtonGroup,
  ToggleButton,
  Slider,
  IconButton,
} from '@mui/material'
import {
  Download as DownloadIcon,
  ArrowBack as ArrowBackIcon,
  PlayArrow as PlayArrowIcon,
  Pause as PauseIcon,
} from '@mui/icons-material'
import { MapContainer, TileLayer, Marker, GeoJSON, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import Layout from '../components/Layout'
import { useMissionStore } from '../stores/missionStore'
import { apiClient } from '../services/api'
import L from 'leaflet'
import type { TimestepContour } from '../types'

// Fix for default marker icon - use CDN instead of local imports
const DefaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
})

L.Marker.prototype.options.icon = DefaultIcon

// Component to update map center when coordinates change
function MapCenterUpdater({ center }: { center: [number, number] }) {
  const map = useMap()
  
  useEffect(() => {
    map.setView(center, map.getZoom(), { animate: true })
  }, [center])
  
  return null
}

export default function ResultsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { currentMission, currentResult, fetchMission, fetchMissionResults, isLoading, error } =
    useMissionStore()
  const [selectedLayer, setSelectedLayer] = useState<'50' | '90' | 'both'>('both')
  const [timeStepIndex, setTimeStepIndex] = useState<number>(0)
  const [isPlaying, setIsPlaying] = useState<boolean>(false)

  // Get timestep contours or use final result as fallback
  const timestepContours = currentResult?.timestepContours || []
  const maxTimeSteps = timestepContours.length
  
  // Auto-play functionality
  useEffect(() => {
    if (!isPlaying || maxTimeSteps === 0) return
    
    const interval = setInterval(() => {
      setTimeStepIndex((prev) => {
        if (prev >= maxTimeSteps - 1) {
          setIsPlaying(false)
          return prev
        }
        return prev + 1
      })
    }, 1000) // 1 second per step
    
    return () => clearInterval(interval)
  }, [isPlaying, maxTimeSteps])
  
  // Reset to last step when data loads
  useEffect(() => {
    if (maxTimeSteps > 0) {
      setTimeStepIndex(maxTimeSteps - 1)
    }
  }, [maxTimeSteps])

  useEffect(() => {
    if (id) {
      fetchMission(id)
      fetchMissionResults(id)
    }
  }, [id, fetchMission, fetchMissionResults])

  const handleDownload = async (format: 'netcdf' | 'geojson' | 'pdf') => {
    if (!id) return

    try {
      const blob = await apiClient.downloadMissionResults(id, format)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `mission-${id}-results.${
        format === 'netcdf' ? 'nc' : format === 'geojson' ? 'json' : 'pdf'
      }`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Download failed:', error)
    }
  }

  if (isLoading && !currentMission) {
    return (
      <Layout>
        <Container maxWidth="xl">
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
        <Container maxWidth="xl">
          <Alert severity="error">{error || 'Mission not found'}</Alert>
          <Button onClick={() => navigate('/missions')} sx={{ mt: 2 }}>
            Back to Missions
          </Button>
        </Container>
      </Layout>
    )
  }

  if (currentMission.status !== 'completed') {
    return (
      <Layout>
        <Container maxWidth="xl">
          <Alert severity="info">
            Mission is still {currentMission.status}. Results will be available when the mission is completed.
          </Alert>
          <Button onClick={() => navigate(`/missions/${id}`)} sx={{ mt: 2 }}>
            Back to Mission Details
          </Button>
        </Container>
      </Layout>
    )
  }

  const mapCenter: [number, number] = currentResult?.centroidLat && currentResult?.centroidLon
    ? [currentResult.centroidLat, currentResult.centroidLon]
    : [currentMission.lastKnownLat, currentMission.lastKnownLon]

  // Get current timestep data or fall back to final result
  const currentTimestep: TimestepContour | null = 
    maxTimeSteps > 0 && timestepContours[timeStepIndex]
      ? timestepContours[timeStepIndex]
      : (currentResult 
          ? {
              time_index: 0,
              timestamp: currentResult.centroidTime || '',
              hours_elapsed: 0,
              centroid_lat: currentResult.centroidLat || 0,
              centroid_lon: currentResult.centroidLon || 0,
              search_area_50_geom: currentResult.searchArea50Geom,
              search_area_90_geom: currentResult.searchArea90Geom,
            }
          : null)

  // Update map center to follow the drift
  const currentMapCenter: [number, number] = currentTimestep
    ? [currentTimestep.centroid_lat, currentTimestep.centroid_lon]
    : mapCenter

  return (
    <Layout>
      <Container maxWidth="xl">
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Button
              startIcon={<ArrowBackIcon />}
              onClick={() => navigate(`/missions/${id}`)}
              sx={{ mb: 1 }}
            >
              Back to Mission
            </Button>
            <Typography variant="h4">{currentMission.name} - Results</Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
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
              onClick={() => handleDownload('pdf')}
            >
              PDF Report
            </Button>
          </Box>
        </Box>

        <Grid container spacing={3}>
          {/* Map */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 2 }}>
              <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">Drift Forecast Map</Typography>
                <ToggleButtonGroup
                  value={selectedLayer}
                  exclusive
                  onChange={(_e, value) => value && setSelectedLayer(value)}
                  size="small"
                >
                  <ToggleButton value="50">50% Area</ToggleButton>
                  <ToggleButton value="90">90% Area</ToggleButton>
                  <ToggleButton value="both">Both</ToggleButton>
                </ToggleButtonGroup>
              </Box>

              <Box sx={{ height: 600 }}>
                <MapContainer
                  center={currentMapCenter}
                  zoom={8}
                  style={{ height: '100%', width: '100%' }}
                >
                  <MapCenterUpdater center={currentMapCenter} />
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />

                  {/* Last known position */}
                  <Marker position={[currentMission.lastKnownLat, currentMission.lastKnownLon]}>
                    <Popup>
                      <strong>Last Known Position</strong>
                      <br />
                      {new Date(currentMission.lastKnownTime).toLocaleString()}
                    </Popup>
                  </Marker>

                  {/* Centroid/Most likely position at current time step */}
                  {currentTimestep && (
                    <Marker
                      position={[currentTimestep.centroid_lat, currentTimestep.centroid_lon]}
                      icon={L.icon({
                        iconUrl: 'data:image/svg+xml;base64,' + btoa(`
                          <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30">
                            <circle cx="15" cy="15" r="10" fill="red" opacity="0.7" stroke="white" stroke-width="2"/>
                          </svg>
                        `),
                        iconSize: [30, 30],
                        iconAnchor: [15, 15],
                      })}
                    >
                      <Popup>
                        <strong>Most Likely Position</strong>
                        <br />
                        {currentTimestep.timestamp &&
                          new Date(currentTimestep.timestamp).toLocaleString()}
                        <br />
                        Hours elapsed: {currentTimestep.hours_elapsed.toFixed(1)}
                      </Popup>
                    </Marker>
                  )}

                  {/* Search areas at current time step */}
                  {(selectedLayer === '50' || selectedLayer === 'both') &&
                    currentTimestep?.search_area_50_geom && (
                      <GeoJSON
                        key={`50-${timeStepIndex}`}
                        data={currentTimestep.search_area_50_geom as any}
                        style={{ color: '#FFA500', fillColor: '#FFA500', fillOpacity: 0.3 }}
                      />
                    )}

                  {(selectedLayer === '90' || selectedLayer === 'both') &&
                    currentTimestep?.search_area_90_geom && (
                      <GeoJSON
                        key={`90-${timeStepIndex}`}
                        data={currentTimestep.search_area_90_geom as any}
                        style={{ color: '#FF0000', fillColor: '#FF0000', fillOpacity: 0.2 }}
                      />
                    )}
                </MapContainer>
              </Box>

              {/* Time slider control */}
              {maxTimeSteps > 0 && (
                <Box sx={{ mt: 2, px: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <IconButton
                      onClick={() => setIsPlaying(!isPlaying)}
                      size="small"
                      color="primary"
                    >
                      {isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
                    </IconButton>
                    <Box sx={{ flex: 1 }}>
                      <Slider
                        value={timeStepIndex}
                        onChange={(_e, value) => {
                          setTimeStepIndex(value as number)
                          setIsPlaying(false)
                        }}
                        min={0}
                        max={maxTimeSteps - 1}
                        step={1}
                        marks={[
                          { value: 0, label: '0h' },
                          { 
                            value: Math.floor((maxTimeSteps - 1) / 2), 
                            label: `${timestepContours[Math.floor((maxTimeSteps - 1) / 2)]?.hours_elapsed.toFixed(0) || ''}h` 
                          },
                          { 
                            value: maxTimeSteps - 1, 
                            label: `${timestepContours[maxTimeSteps - 1]?.hours_elapsed.toFixed(0) || ''}h` 
                          },
                        ]}
                        valueLabelDisplay="auto"
                        valueLabelFormat={(value) => {
                          const ts = timestepContours[value]
                          return ts ? `${ts.hours_elapsed.toFixed(1)}h` : ''
                        }}
                      />
                    </Box>
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 1 }}>
                    {currentTimestep && new Date(currentTimestep.timestamp).toLocaleString()} 
                    {' '}(+{currentTimestep?.hours_elapsed.toFixed(1)}h from last known position)
                  </Typography>
                </Box>
              )}
            </Paper>
          </Grid>

          {/* Results Summary */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Forecast Summary
              </Typography>

              {currentResult ? (
                <Box>
                  {currentResult.centroidLat && currentResult.centroidLon && (
                    <Card variant="outlined" sx={{ mb: 2 }}>
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          Most Likely Position
                        </Typography>
                        <Typography variant="body1">
                          Lat: {currentResult.centroidLat.toFixed(6)}°
                        </Typography>
                        <Typography variant="body1">
                          Lon: {currentResult.centroidLon.toFixed(6)}°
                        </Typography>
                        {currentResult.centroidTime && (
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            {new Date(currentResult.centroidTime).toLocaleString()}
                          </Typography>
                        )}
                      </CardContent>
                    </Card>
                  )}

                  <Card variant="outlined" sx={{ mb: 2 }}>
                    <CardContent>
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        Simulation Statistics
                      </Typography>
                      {currentResult.particleCount && (
                        <Typography variant="body2">
                          Particles: {currentResult.particleCount.toLocaleString()}
                        </Typography>
                      )}
                      {currentResult.strandedCount !== undefined && (
                        <Typography variant="body2">
                          Stranded: {currentResult.strandedCount.toLocaleString()}
                        </Typography>
                      )}
                      {currentResult.computationTimeSeconds && (
                        <Typography variant="body2">
                          Computation Time: {currentResult.computationTimeSeconds.toFixed(1)}s
                        </Typography>
                      )}
                    </CardContent>
                  </Card>

                  <Typography variant="body2" color="text.secondary">
                    Results generated: {new Date(currentResult.createdAt).toLocaleString()}
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ textAlign: 'center', py: 2 }}>
                  <CircularProgress size={30} />
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                    Loading results...
                  </Typography>
                </Box>
              )}
            </Paper>

            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Legend
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box
                    sx={{
                      width: 20,
                      height: 20,
                      bgcolor: '#FFA500',
                      opacity: 0.5,
                      border: '1px solid #FFA500',
                    }}
                  />
                  <Typography variant="body2">50% Probability Area</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box
                    sx={{
                      width: 20,
                      height: 20,
                      bgcolor: '#FF0000',
                      opacity: 0.3,
                      border: '1px solid #FF0000',
                    }}
                  />
                  <Typography variant="body2">90% Probability Area</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box
                    sx={{
                      width: 20,
                      height: 20,
                      bgcolor: 'red',
                      borderRadius: '50%',
                    }}
                  />
                  <Typography variant="body2">Most Likely Position</Typography>
                </Box>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      </Container>
    </Layout>
  )
}
