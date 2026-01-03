-- Add time-step contours for drift evolution visualization
-- This allows the UI to show how the 50% and 90% probability areas evolve over time

ALTER TABLE mission_results 
ADD COLUMN IF NOT EXISTS timestep_contours JSONB;

-- The timestep_contours column will store an array of objects with this structure:
-- [
--   {
--     "time_index": 0,
--     "timestamp": "2024-01-01T12:00:00Z",
--     "hours_elapsed": 0,
--     "centroid_lat": 60.0,
--     "centroid_lon": 5.0,
--     "search_area_50_geom": {...},  -- GeoJSON polygon
--     "search_area_90_geom": {...}   -- GeoJSON polygon
--   },
--   ...
-- ]
