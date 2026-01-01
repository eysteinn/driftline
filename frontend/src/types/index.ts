// User and Authentication Types
export interface User {
  id: string
  email: string
  fullName: string
  isActive: boolean
  isVerified: boolean
  role: string
  createdAt: string
  updatedAt: string
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  fullName: string
}

// Mission Types
export interface Mission {
  id: string
  userId: string
  name: string
  description?: string
  lastKnownLat: number
  lastKnownLon: number
  lastKnownTime: string
  objectType: string
  uncertaintyRadiusM?: number
  forecastHours: number
  ensembleSize: number
  config?: Record<string, any>
  status: MissionStatus
  jobId?: string
  createdAt: string
  updatedAt: string
  completedAt?: string
}

export type MissionStatus = 
  | 'created' 
  | 'queued' 
  | 'processing' 
  | 'completed' 
  | 'failed'

export interface CreateMissionRequest {
  name: string
  description?: string
  lastKnownLat: number
  lastKnownLon: number
  lastKnownTime: string
  objectType: string
  uncertaintyRadiusM?: number
  forecastHours: number
  ensembleSize?: number
  config?: Record<string, any>
}

// Mission Results Types
export interface MissionResult {
  id: string
  missionId: string
  centroidLat?: number
  centroidLon?: number
  centroidTime?: string
  searchArea50Geom?: GeoJSON.Geometry
  searchArea90Geom?: GeoJSON.Geometry
  netcdfPath?: string
  geojsonPath?: string
  pdfReportPath?: string
  particleCount?: number
  strandedCount?: number
  computationTimeSeconds?: number
  createdAt: string
}

// Object Types
export const OBJECT_TYPES = [
  'PIW',  // Person in Water
  'Life Raft',
  'Small Boat',
  'Fishing Vessel',
  'Container',
  'Debris Field',
] as const

export type ObjectType = typeof OBJECT_TYPES[number]

// API Response Types
export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface ApiError {
  error: string
  message: string
  statusCode: number
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  perPage: number
}

// WebSocket Message Types
export interface WebSocketMessage {
  type: 'status_update' | 'error' | 'complete'
  missionId: string
  status?: MissionStatus
  progress?: number
  message?: string
  error?: string
}

// Billing Types
export interface Subscription {
  id: string
  userId: string
  plan: string
  status: string
  currentPeriodStart?: string
  currentPeriodEnd?: string
  cancelAtPeriodEnd: boolean
  createdAt: string
}

export interface UsageRecord {
  id: string
  userId: string
  missionId?: string
  usageType: string
  quantity: number
  amountCents: number
  recordedAt: string
}

export interface ApiKey {
  id: string
  userId: string
  name: string
  keyPreview: string  // Only first/last few characters
  scopes?: string[]
  isActive: boolean
  lastUsedAt?: string
  createdAt: string
  expiresAt?: string
}
