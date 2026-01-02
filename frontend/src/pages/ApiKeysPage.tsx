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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormHelperText,
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
  const [expiresInDays, setExpiresInDays] = useState<string>('never')
  const [customDays, setCustomDays] = useState<string>('')
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

    // Calculate expiresInDays value
    let expiryDays: number | null = null
    if (expiresInDays === 'custom') {
      const days = parseInt(customDays)
      if (isNaN(days) || days <= 0) {
        setError('Please enter a valid number of days')
        return
      }
      expiryDays = days
    } else if (expiresInDays !== 'never') {
      expiryDays = parseInt(expiresInDays)
    }

    setCreating(true)
    setError(null)
    try {
      const response = await apiClient.createApiKey(newKeyName, expiryDays)
      setNewKeyValue(response.key)
      await fetchApiKeys()
      setNewKeyName('')
      setExpiresInDays('never')
      setCustomDays('')
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
    setExpiresInDays('never')
    setCustomDays('')
  }

  const isExpired = (expiresAt?: string) => {
    if (!expiresAt) return false
    return new Date(expiresAt) < new Date()
  }

  const formatExpiration = (expiresAt?: string) => {
    if (!expiresAt) return 'Never'
    const expDate = new Date(expiresAt)
    const now = new Date()
    if (expDate < now) return 'Expired'
    return expDate.toLocaleDateString()
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
                    <TableCell>Expires</TableCell>
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
                          label={
                            isExpired(key.expiresAt)
                              ? 'Expired'
                              : key.isActive
                              ? 'Active'
                              : 'Inactive'
                          }
                          color={
                            isExpired(key.expiresAt)
                              ? 'error'
                              : key.isActive
                              ? 'success'
                              : 'default'
                          }
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{formatExpiration(key.expiresAt)}</TableCell>
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
                <FormControl fullWidth margin="normal">
                  <InputLabel id="expiration-label">Expiration</InputLabel>
                  <Select
                    labelId="expiration-label"
                    value={expiresInDays}
                    label="Expiration"
                    onChange={(e) => setExpiresInDays(e.target.value)}
                  >
                    <MenuItem value="never">Never expires</MenuItem>
                    <MenuItem value="7">7 days</MenuItem>
                    <MenuItem value="30">30 days</MenuItem>
                    <MenuItem value="90">90 days</MenuItem>
                    <MenuItem value="365">1 year</MenuItem>
                    <MenuItem value="custom">Custom...</MenuItem>
                  </Select>
                  <FormHelperText>
                    Choose when this API key should expire, or never for infinite lifetime
                  </FormHelperText>
                </FormControl>
                {expiresInDays === 'custom' && (
                  <TextField
                    fullWidth
                    type="number"
                    label="Custom Days"
                    value={customDays}
                    onChange={(e) => setCustomDays(e.target.value)}
                    margin="normal"
                    placeholder="Enter number of days"
                    inputProps={{ min: 1 }}
                  />
                )}
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
