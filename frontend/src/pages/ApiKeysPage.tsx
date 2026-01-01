import { useState, useEffect } from 'react'
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
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Chip,
  Card,
  CardContent,
  CircularProgress,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ContentCopy as CopyIcon,
} from '@mui/icons-material'
import Layout from '../components/Layout'
import { apiClient } from '../services/api'
import type { ApiKey } from '../types'

export default function ApiKeysPage() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    fetchApiKeys()
  }, [])

  const fetchApiKeys = async () => {
    setIsLoading(true)
    try {
      const keys = await apiClient.getApiKeys()
      setApiKeys(keys)
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to fetch API keys')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) return

    setCreating(true)
    setError(null)
    try {
      const response = await apiClient.createApiKey(newKeyName)
      setNewKeyValue(response.key)
      await fetchApiKeys()
      setNewKeyName('')
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to create API key')
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteKey = async (id: string) => {
    if (!confirm('Are you sure you want to delete this API key? This action cannot be undone.')) {
      return
    }

    try {
      await apiClient.deleteApiKey(id)
      await fetchApiKeys()
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to delete API key')
    }
  }

  const handleCopyKey = (key: string) => {
    navigator.clipboard.writeText(key)
  }

  const handleCloseDialog = () => {
    setCreateDialogOpen(false)
    setNewKeyValue(null)
    setNewKeyName('')
  }

  return (
    <Layout>
      <Container maxWidth="lg">
        <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h4">API Keys</Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Create API Key
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Paper sx={{ mb: 3, p: 3 }}>
          <Typography variant="body1" gutterBottom>
            API keys allow you to authenticate API requests without using your login credentials.
            Keep your API keys secure and never share them publicly.
          </Typography>
        </Paper>

        <Paper>
          {isLoading ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <CircularProgress />
            </Box>
          ) : apiKeys.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Typography color="text.secondary">
                No API keys yet. Create your first API key to get started.
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Key</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Last Used</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {apiKeys.map((key) => (
                    <TableRow key={key.id}>
                      <TableCell>{key.name}</TableCell>
                      <TableCell>
                        <code>{key.keyPreview}</code>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={key.isActive ? 'Active' : 'Inactive'}
                          color={key.isActive ? 'success' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        {key.lastUsedAt
                          ? new Date(key.lastUsedAt).toLocaleString()
                          : 'Never'}
                      </TableCell>
                      <TableCell>{new Date(key.createdAt).toLocaleDateString()}</TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          onClick={() => handleDeleteKey(key.id)}
                          color="error"
                          title="Delete"
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

        {/* Create API Key Dialog */}
        <Dialog open={createDialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
          <DialogTitle>
            {newKeyValue ? 'API Key Created' : 'Create New API Key'}
          </DialogTitle>
          <DialogContent>
            {newKeyValue ? (
              <Box>
                <Alert severity="warning" sx={{ mb: 2 }}>
                  Make sure to copy your API key now. You won't be able to see it again!
                </Alert>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Your API Key:
                    </Typography>
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        bgcolor: 'grey.100',
                        p: 2,
                        borderRadius: 1,
                      }}
                    >
                      <code style={{ flex: 1, wordBreak: 'break-all' }}>{newKeyValue}</code>
                      <IconButton
                        size="small"
                        onClick={() => handleCopyKey(newKeyValue)}
                        title="Copy to clipboard"
                      >
                        <CopyIcon />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              </Box>
            ) : (
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Give your API key a descriptive name to help you identify it later.
                </Typography>
                <TextField
                  autoFocus
                  fullWidth
                  label="Key Name"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  margin="normal"
                  placeholder="e.g., Production Server"
                />
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            {newKeyValue ? (
              <Button onClick={handleCloseDialog}>Close</Button>
            ) : (
              <>
                <Button onClick={handleCloseDialog}>Cancel</Button>
                <Button
                  onClick={handleCreateKey}
                  variant="contained"
                  disabled={!newKeyName.trim() || creating}
                >
                  {creating ? <CircularProgress size={24} /> : 'Create'}
                </Button>
              </>
            )}
          </DialogActions>
        </Dialog>
      </Container>
    </Layout>
  )
}
