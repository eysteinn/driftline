# Time Slider UI Description

## Visual Layout

The time slider feature appears on the Results page below the map visualization. Here's what users will see:

### Location
- **Position**: Directly below the Leaflet map (within the same paper container)
- **Visibility**: Only appears when time-step contours are available

### Components

#### 1. Play/Pause Button
- **Icon**: Play arrow (▶) or Pause (⏸) icon
- **Color**: Primary theme color (blue)
- **Size**: Small icon button
- **Behavior**: 
  - Clicking starts/stops automatic animation through time steps
  - Auto-advances every 1 second when playing
  - Automatically pauses when reaching the end

#### 2. Time Slider
- **Type**: Material-UI Slider component
- **Range**: 0 to (number of time steps - 1)
- **Marks**: Three labeled marks:
  - Start: "0h"
  - Middle: "{middle_hours}h" (only shown if more than 2 steps)
  - End: "{total_hours}h"
- **Value Label**: Appears above the slider thumb when dragging
  - Format: "{hours_elapsed}h" (e.g., "12.5h")
- **Behavior**:
  - Dragging pauses auto-play
  - Updates map in real-time as slider moves

#### 3. Time Display
- **Type**: Typography caption
- **Color**: Secondary text color (gray)
- **Content**: Shows two pieces of information:
  - Current timestamp in local format (e.g., "1/15/2024, 2:30:00 PM")
  - Hours elapsed from last known position (e.g., "(+12.5h from last known position)")
- **Alignment**: Centered below the slider

### Map Changes During Time Scrubbing

As the user moves the slider or plays through time:

1. **Centroid Marker (Red Circle)**
   - Position updates to show the most likely position at that time step
   - Popup shows:
     - "Most Likely Position"
     - Timestamp
     - Hours elapsed

2. **50% Probability Area (Orange)**
   - Updates to show the area at that time step
   - Color: Orange (#FFA500) with 30% fill opacity

3. **90% Probability Area (Red)**
   - Updates to show the area at that time step
   - Color: Red (#FF0000) with 20% fill opacity

4. **Map Center**
   - Smoothly follows the centroid as it drifts
   - Uses animated transitions

5. **Last Known Position Marker (Blue)**
   - Remains fixed at the starting location
   - Provides reference point

### Example Timeline

For a 24-hour forecast with hourly output:
```
|-------|-------|-------|-------|
0h      6h      12h     18h     24h
▶ [==================●=========] 
     "1/15/2024, 2:30:00 PM (+12.5h from last known position)"
```

### Responsive Behavior

- On mobile devices (< 768px):
  - Slider takes full width
  - Play button remains visible
  - Time display wraps if needed
  
- On tablets and desktops:
  - All components fit in a single row
  - Slider expands to fill available space

### Color Scheme

- Play/Pause button: Primary blue (#1976d2)
- Slider track: Gray (#bdbdbd) 
- Slider thumb: Primary blue (#1976d2)
- Time text: Gray secondary (#666)
- Map contours: Orange (#FFA500) and Red (#FF0000)

### User Interactions

1. **Manual Scrubbing**: Click/drag slider to any position
2. **Auto-play**: Click play to watch evolution
3. **Pause**: Click pause or drag slider to stop
4. **Jump to Time**: Click on slider track to jump to that position
5. **View Details**: Click centroid marker to see popup with details

## Example Use Case

A search and rescue coordinator:
1. Opens a completed mission's results
2. Sees the final drift position
3. Notices the time slider below the map
4. Clicks play to see how the drift evolved
5. Pauses at 12 hours to see where to focus initial search
6. Scrubs back and forth to understand drift patterns
7. Notes that the drift direction changed at 18 hours
8. Uses this information to plan search strategy
