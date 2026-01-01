import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Container,
  Paper,
  Typography,
  Box,
  TextField,
  Button,
  Grid,
  MenuItem,
  Alert,
  CircularProgress,
} from '@mui/material'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import Layout from '../components/Layout'
import { useMissionStore } from '../stores/missionStore'
import { OBJECT_TYPES } from '../types'

// Fix for default marker icon - use CDN instead of local imports
import L from 'leaflet'

const DefaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41]
})

L.Marker.prototype.options.icon = DefaultIcon

interface MapClickHandlerProps {
  onLocationSelect: (lat: number, lon: number) => void
}

function MapClickHandler({ onLocationSelect }: MapClickHandlerProps) {
  useMapEvents({
    click: (e) => {
      onLocationSelect(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

export default function NewMissionPage() {
  const navigate = useNavigate()
  const { createMission, isLoading, error, clearError } = useMissionStore()

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    lastKnownLat: 64.5,
    lastKnownLon: -18.2,
    lastKnownTime: new Date().toISOString().slice(0, 16),
    objectType: 'PIW',
    uncertaintyRadiusM: 5000,
    forecastHours: 48,
    ensembleSize: 1000,
  })

  const [markerPosition, setMarkerPosition] = useState<L.LatLng>(
    new L.LatLng(formData.lastKnownLat, formData.lastKnownLon)
  )

  const handleChange = (field: string, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    
    // Update marker if coordinates change
    if (field === 'lastKnownLat' || field === 'lastKnownLon') {
      const lat = field === 'lastKnownLat' ? value : formData.lastKnownLat
      const lon = field === 'lastKnownLon' ? value : formData.lastKnownLon
      if (!isNaN(lat) && !isNaN(lon)) {
        setMarkerPosition(new L.LatLng(lat, lon))
      }
    }
  }

  const handleMapClick = (lat: number, lon: number) => {
    setFormData((prev) => ({
      ...prev,
      lastKnownLat: parseFloat(lat.toFixed(6)),
      lastKnownLon: parseFloat(lon.toFixed(6)),
    }))
    setMarkerPosition(new L.LatLng(lat, lon))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()

    try {
      const mission = await createMission({
        ...formData,
        lastKnownTime: new Date(formData.lastKnownTime).toISOString(),
      })
      navigate(`/missions/${mission.id}`)
    } catch (error) {
      // Error is handled by store
    }
  }

  return (
    <Layout>
      <Container maxWidth="lg">
        <Typography variant="h4" gutterBottom>
          Create New Mission
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
            {error}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            {/* Form Section */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Mission Details
                </Typography>

                <TextField
                  fullWidth
                  label="Mission Name"
                  required
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  margin="normal"
                />

                <TextField
                  fullWidth
                  label="Description"
                  multiline
                  rows={3}
                  value={formData.description}
                  onChange={(e) => handleChange('description', e.target.value)}
                  margin="normal"
                />

                <TextField
                  fullWidth
                  select
                  label="Object Type"
                  required
                  value={formData.objectType}
                  onChange={(e) => handleChange('objectType', e.target.value)}
                  margin="normal"
                  helperText="Type of object for drift calculation"
                >
                  {OBJECT_TYPES.map((type) => (
                    <MenuItem key={type} value={type}>
                      {type}
                    </MenuItem>
                  ))}
                </TextField>

                <TextField
                  fullWidth
                  label="Last Known Time"
                  type="datetime-local"
                  required
                  value={formData.lastKnownTime}
                  onChange={(e) => handleChange('lastKnownTime', e.target.value)}
                  margin="normal"
                  InputLabelProps={{ shrink: true }}
                />

                <Grid container spacing={2} sx={{ mt: 1 }}>
                  <Grid item xs={6}>
                    <TextField
                      fullWidth
                      label="Latitude"
                      type="number"
                      required
                      value={formData.lastKnownLat}
                      onChange={(e) => handleChange('lastKnownLat', parseFloat(e.target.value))}
                      inputProps={{ step: 0.000001, min: -90, max: 90 }}
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <TextField
                      fullWidth
                      label="Longitude"
                      type="number"
                      required
                      value={formData.lastKnownLon}
                      onChange={(e) => handleChange('lastKnownLon', parseFloat(e.target.value))}
                      inputProps={{ step: 0.000001, min: -180, max: 180 }}
                    />
                  </Grid>
                </Grid>

                <TextField
                  fullWidth
                  label="Uncertainty Radius (meters)"
                  type="number"
                  value={formData.uncertaintyRadiusM}
                  onChange={(e) => handleChange('uncertaintyRadiusM', parseInt(e.target.value))}
                  margin="normal"
                  helperText="Position uncertainty in meters"
                />

                <TextField
                  fullWidth
                  label="Forecast Hours"
                  type="number"
                  required
                  value={formData.forecastHours}
                  onChange={(e) => handleChange('forecastHours', parseInt(e.target.value))}
                  margin="normal"
                  inputProps={{ min: 1, max: 168 }}
                  helperText="Number of hours to forecast (1-168)"
                />

                <TextField
                  fullWidth
                  label="Ensemble Size"
                  type="number"
                  value={formData.ensembleSize}
                  onChange={(e) => handleChange('ensembleSize', parseInt(e.target.value))}
                  margin="normal"
                  inputProps={{ min: 100, max: 10000 }}
                  helperText="Number of particles (100-10000)"
                />

                <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                  <Button
                    type="submit"
                    variant="contained"
                    size="large"
                    disabled={isLoading}
                    fullWidth
                  >
                    {isLoading ? <CircularProgress size={24} /> : 'Create Mission'}
                  </Button>
                  <Button
                    variant="outlined"
                    size="large"
                    onClick={() => navigate('/missions')}
                    disabled={isLoading}
                  >
                    Cancel
                  </Button>
                </Box>
              </Paper>
            </Grid>

            {/* Map Section */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Last Known Position
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Click on the map to set the position
                </Typography>

                <Box sx={{ height: 600, mt: 2 }}>
                  <MapContainer
                    center={[formData.lastKnownLat, formData.lastKnownLon]}
                    zoom={6}
                    style={{ height: '100%', width: '100%' }}
                  >
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <Marker position={markerPosition} />
                    <MapClickHandler onLocationSelect={handleMapClick} />
                  </MapContainer>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </Box>
      </Container>
    </Layout>
  )
}
