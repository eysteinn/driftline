import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  CircularProgress,
} from '@mui/material'
import {
  Add as AddIcon,
  Visibility as VisibilityIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'
import { useMissionStore } from '../stores/missionStore'
import Layout from '../components/Layout'

export default function MissionsPage() {
  const navigate = useNavigate()
  const { missions, fetchMissions, deleteMission, isLoading } = useMissionStore()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [missionToDelete, setMissionToDelete] = useState<string | null>(null)

  useEffect(() => {
    fetchMissions()
  }, [fetchMissions])

  const handleDeleteClick = (id: string) => {
    setMissionToDelete(id)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (missionToDelete) {
      await deleteMission(missionToDelete)
      setDeleteDialogOpen(false)
      setMissionToDelete(null)
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

  return (
    <Layout>
      <Container maxWidth="lg">
        <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h4">Missions</Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={() => fetchMissions()}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => navigate('/missions/new')}
            >
              New Mission
            </Button>
          </Box>
        </Box>

        <Paper>
          {isLoading && missions.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <CircularProgress />
            </Box>
          ) : missions.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Typography color="text.secondary">
                No missions yet. Create your first mission to get started!
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Object Type</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Forecast (hrs)</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {missions.map((mission) => (
                    <TableRow key={mission.id} hover>
                      <TableCell>
                        <Typography variant="body1" fontWeight="medium">
                          {mission.name}
                        </Typography>
                        {mission.description && (
                          <Typography variant="body2" color="text.secondary">
                            {mission.description}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>{mission.objectType}</TableCell>
                      <TableCell>
                        <Chip
                          label={mission.status}
                          color={getStatusColor(mission.status) as any}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{mission.forecastHours}</TableCell>
                      <TableCell>
                        {new Date(mission.createdAt).toLocaleDateString()}
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          onClick={() => navigate(`/missions/${mission.id}`)}
                          title="View details"
                        >
                          <VisibilityIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleDeleteClick(mission.id)}
                          title="Delete"
                          color="error"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>

        {/* Delete Confirmation Dialog */}
        <Dialog
          open={deleteDialogOpen}
          onClose={() => setDeleteDialogOpen(false)}
        >
          <DialogTitle>Delete Mission</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Are you sure you want to delete this mission? This action cannot be undone.
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleDeleteConfirm} color="error" autoFocus>
              Delete
            </Button>
          </DialogActions>
        </Dialog>
      </Container>
    </Layout>
  )
}
