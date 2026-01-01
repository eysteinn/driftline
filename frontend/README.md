# Driftline Frontend

React + TypeScript frontend application for the Driftline SAR drift forecasting platform.

## 🎯 Overview

The frontend provides a modern, responsive web interface for creating and managing SAR (Search and Rescue) drift forecast missions. Built with React 18, TypeScript, Material-UI, and Leaflet for interactive mapping.

## 🏗️ Architecture

### Technology Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite 5
- **UI Library**: Material-UI (MUI) v5
- **State Management**: Zustand
- **Data Fetching**: React Query (TanStack Query)
- **Routing**: React Router v6
- **Mapping**: Leaflet + React-Leaflet
- **HTTP Client**: Axios

### Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── Layout.tsx    # Main app layout with navigation
│   │   └── PrivateRoute.tsx  # Protected route wrapper
│   ├── pages/           # Page components
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── MissionsPage.tsx
│   │   ├── NewMissionPage.tsx
│   │   ├── MissionDetailsPage.tsx
│   │   ├── ResultsPage.tsx
│   │   ├── ProfilePage.tsx
│   │   └── ApiKeysPage.tsx
│   ├── services/        # API clients
│   │   └── api.ts       # Axios API client with interceptors
│   ├── stores/          # Zustand state stores
│   │   ├── authStore.ts     # Authentication state
│   │   └── missionStore.ts  # Mission management state
│   ├── types/           # TypeScript type definitions
│   │   └── index.ts
│   ├── App.tsx          # Main app component with routing
│   ├── main.tsx         # Application entry point
│   └── index.css        # Global styles
├── package.json
├── tsconfig.json
├── vite.config.ts
└── .eslintrc.json
```

## ✨ Features Implemented

### 1. Authentication & User Management
- ✅ Login page with email/password authentication
- ✅ Registration page with validation
- ✅ JWT token management with automatic refresh
- ✅ Protected routes requiring authentication
- ✅ User profile management
- ✅ Logout functionality

### 2. Dashboard
- ✅ Overview of missions with statistics
- ✅ Quick access to create new missions
- ✅ Recent missions list with status badges
- ✅ Mission counts by status (total, completed, in progress)

### 3. Mission Management
- ✅ Mission list page with sortable table
- ✅ Mission creation form with interactive map
- ✅ Click-to-place position selection on map
- ✅ Configurable mission parameters:
  - Object type (PIW, Life Raft, Small Boat, etc.)
  - Last known position (lat/lon)
  - Last known time
  - Forecast hours
  - Ensemble size
  - Uncertainty radius
- ✅ Mission details page with full information
- ✅ Mission deletion with confirmation
- ✅ Real-time status tracking

### 4. Results Visualization
- ✅ Interactive map showing:
  - Last known position
  - Most likely position (centroid)
  - 50% probability search area
  - 90% probability search area
- ✅ Layer toggle controls
- ✅ Simulation statistics display
- ✅ Download results in multiple formats (GeoJSON, NetCDF, PDF)
- ✅ Legend showing area colors and markers

### 5. API Key Management
- ✅ List API keys with metadata
- ✅ Create new API keys
- ✅ Copy key to clipboard
- ✅ Delete API keys
- ✅ Show key preview for security
- ✅ Display last used timestamp

### 6. UI/UX Features
- ✅ Responsive design (mobile and desktop)
- ✅ Sidebar navigation with collapsible menu
- ✅ Material Design components
- ✅ Loading states and spinners
- ✅ Error handling with user-friendly messages
- ✅ Form validation
- ✅ Success/error notifications

## 🚀 Getting Started

### Prerequisites

- Node.js 20+ and npm
- Backend API running (default: http://localhost:8000)

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Application will be available at http://localhost:3000

### Building for Production

```bash
npm run build
```

Build output will be in `dist/` directory.

### Linting

```bash
npm run lint
```

## 🔧 Configuration

Environment variables (create `.env` file):

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws
VITE_MAP_TILE_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
```

## 📡 API Integration

The frontend communicates with the backend API using Axios with the following features:

- **Authentication**: JWT tokens in Authorization header
- **Token Refresh**: Automatic token refresh on 401 errors
- **Request Interceptors**: Add auth headers to all requests
- **Error Handling**: Centralized error handling
- **Type Safety**: Full TypeScript types for API requests/responses

### API Client Usage

```typescript
import { apiClient } from './services/api'

// Create a mission
const mission = await apiClient.createMission({
  name: 'SAR Mission 1',
  lastKnownLat: 64.5,
  lastKnownLon: -18.2,
  objectType: 'PIW',
  forecastHours: 48
})

// Get missions
const missions = await apiClient.getMissions()
```

## 🗺️ Map Integration

Uses Leaflet for interactive mapping:

- Click-to-place markers
- Display GeoJSON polygons
- Custom marker icons
- Multiple tile layer support
- Responsive map containers

## 🔐 State Management

Uses Zustand for lightweight state management:

### Auth Store
- User authentication state
- Login/logout actions
- Token persistence
- Current user data

### Mission Store
- Mission list
- Current mission details
- Mission results
- CRUD operations

## 📱 Responsive Design

The application is fully responsive:

- **Desktop**: Full sidebar navigation, multi-column layouts
- **Mobile**: Collapsible drawer menu, stacked layouts
- **Tablet**: Optimized layouts for medium screens

## 🎨 Theming

Material-UI theme customization:

```typescript
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
```

## 🧪 Testing

Currently implemented:
- TypeScript type checking
- ESLint code quality checks
- Build verification

Future additions:
- Unit tests with Vitest
- Component tests with React Testing Library
- E2E tests with Playwright

## 📦 Dependencies

### Core Dependencies
- `react` & `react-dom` - UI framework
- `react-router-dom` - Routing
- `@mui/material` - UI components
- `axios` - HTTP client
- `zustand` - State management
- `@tanstack/react-query` - Data fetching
- `leaflet` & `react-leaflet` - Mapping

### Development Dependencies
- `typescript` - Type safety
- `vite` - Build tool
- `eslint` - Code linting
- `@vitejs/plugin-react` - React support for Vite

## 🔄 Future Enhancements

- [ ] WebSocket integration for real-time updates
- [ ] Password reset flow
- [ ] Email verification
- [ ] Billing/subscription management
- [ ] Advanced mission search and filtering
- [ ] Mission history and analytics
- [ ] Export mission reports
- [ ] Multi-language support
- [ ] Dark mode toggle
- [ ] Offline support with PWA

## 📝 Code Style

- TypeScript for type safety
- Functional components with hooks
- Material-UI component library
- Consistent file naming (PascalCase for components)
- ESLint configuration for code quality

## 🐛 Known Issues

- ESLint warnings for `any` types in error handlers (acceptable for MVP)
- Leaflet marker icons need CDN fallback
- Large bundle size (687KB) - consider code splitting for optimization

## 📄 License

Proprietary - All rights reserved

## 🤝 Contributing

See main repository CONTRIBUTING.md for guidelines.
