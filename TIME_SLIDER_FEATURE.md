# Time Slider Feature for Drift Contours

## Overview

This feature adds a time slider to the Results page that allows users to visualize how the 50% and 90% probability contours evolve over time during the drift simulation.

## Changes Made

### Backend Changes

1. **Database Schema** (`sql/migrations/02_add_timestep_contours.sql`)
   - Added `timestep_contours` JSONB column to `mission_results` table
   - Stores an array of contour data for each time step

2. **Results Processor** (`services/results-processor/processor.py`)
   - Added `_calculate_timestep_contours()` method to calculate contours at each time step
   - Modified `_calculate_density_and_contours()` to accept a time index parameter
   - Updated `process_results()` to store time-step contours in the database
   - Optimized to calculate up to 24 snapshots for performance

3. **API Models** (`services/api/internal/models/result.go`)
   - Added `TimestepContours` field to `MissionResult` struct

4. **API Handlers** (`services/api/internal/handlers/missions.go`)
   - Updated `GetMissionResults` to fetch and return timestep contours

### Frontend Changes

1. **Types** (`frontend/src/types/index.ts`)
   - Added `TimestepContour` interface
   - Updated `MissionResult` interface to include `timestepContours`

2. **Results Page** (`frontend/src/pages/ResultsPage.tsx`)
   - Added Material-UI Slider component for time selection
   - Added play/pause button for automatic playback
   - Updated map to display contours based on selected time step
   - Map center follows the drift as time progresses
   - Added time labels showing elapsed hours and timestamp

## Usage

### For Developers

1. Apply the database migration:
   ```bash
   ./migrate_timestep_contours.sh
   ```

2. Rebuild and restart the results processor service:
   ```bash
   docker compose -f docker-compose.dev.yml up --build results-processor -d
   ```

3. Rebuild the API service:
   ```bash
   docker compose -f docker-compose.dev.yml up --build api -d
   ```

4. The frontend will automatically pick up the new data structure

### For Users

1. Create a new mission or view results from a completed mission
2. On the Results page, you'll see a time slider below the map (if time-step data is available)
3. Use the slider to scrub through different time steps
4. Click the play button to automatically animate through the drift evolution
5. The map will show:
   - The most likely position (centroid) at each time step
   - 50% and 90% probability areas at each time step
   - Time elapsed from the last known position

## Data Structure

The `timestep_contours` field contains an array of objects with this structure:

```json
[
  {
    "time_index": 0,
    "timestamp": "2024-01-01T12:00:00Z",
    "hours_elapsed": 0,
    "centroid_lat": 60.0,
    "centroid_lon": 5.0,
    "search_area_50_geom": { /* GeoJSON polygon */ },
    "search_area_90_geom": { /* GeoJSON polygon */ }
  },
  ...
]
```

## Performance Considerations

- The system calculates up to 24 time-step snapshots to balance detail with storage/performance
- For a 24-hour simulation with 1-hour intervals, every time step is captured
- For longer simulations (e.g., 72 hours), time steps are subsampled
- Time-step contours are calculated once during results processing and cached in the database

## Backward Compatibility

- Existing missions without time-step data will still work
- The slider only appears when time-step contours are available
- Falls back to showing final results if no time-step data exists

## Testing

To test the feature:

1. Create a new mission with a 24-hour forecast
2. Wait for the mission to complete
3. View the results page
4. Verify the time slider appears and allows scrubbing through time
5. Test the play/pause functionality
6. Verify contours and centroid position update correctly
