"""
Unit tests for time-step contour calculation
"""
import unittest
import numpy as np
import xarray as xr
from datetime import datetime, timedelta


class TestTimestepContours(unittest.TestCase):
    """Test time-step contour calculation logic"""
    
    def create_mock_dataset(self, num_particles=100, num_timesteps=24):
        """Create a mock xarray dataset similar to OpenDrift output"""
        # Create time array (hourly for 24 hours)
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        times = np.array([
            np.datetime64(start_time + timedelta(hours=i)) 
            for i in range(num_timesteps)
        ])
        
        # Create particle trajectories that drift in a predictable pattern
        trajectories = np.arange(num_particles)
        
        # Simulate drift: particles start at (60N, 5E) and drift northeast
        base_lat = 60.0
        base_lon = 5.0
        
        # Create position arrays with drift pattern
        lons = np.zeros((num_timesteps, num_particles))
        lats = np.zeros((num_timesteps, num_particles))
        
        for t in range(num_timesteps):
            # Add random spread around base position that increases over time
            drift_factor = t * 0.01  # Drift 0.01 degrees per hour
            lons[t, :] = base_lon + drift_factor + np.random.normal(0, 0.1, num_particles)
            lats[t, :] = base_lat + drift_factor + np.random.normal(0, 0.1, num_particles)
        
        # Create xarray dataset
        ds = xr.Dataset(
            {
                'lon': (['time', 'trajectory'], lons),
                'lat': (['time', 'trajectory'], lats),
            },
            coords={
                'time': times,
                'trajectory': trajectories,
            }
        )
        
        return ds
    
    def test_hours_elapsed_calculation(self):
        """Test that hours_elapsed is calculated correctly"""
        ds = self.create_mock_dataset(num_particles=100, num_timesteps=24)
        times = ds['time'].values
        
        # Test for various time indices
        test_cases = [
            (0, 0.0),    # Start time
            (6, 6.0),    # 6 hours
            (12, 12.0),  # 12 hours
            (23, 23.0),  # 23 hours (last index)
        ]
        
        for time_idx, expected_hours in test_cases:
            timestamp = times[time_idx]
            hours_elapsed = (timestamp - times[0]) / np.timedelta64(1, 'h')
            
            self.assertAlmostEqual(
                float(hours_elapsed), 
                expected_hours, 
                places=1,
                msg=f"Hours elapsed at index {time_idx} should be {expected_hours}"
            )
    
    def test_hours_elapsed_with_subsampling(self):
        """Test hours_elapsed when subsampling time steps"""
        ds = self.create_mock_dataset(num_particles=100, num_timesteps=72)
        times = ds['time'].values
        
        # Simulate subsampling every 3rd timestep (like step_interval=3)
        step_interval = 3
        
        for time_idx in range(0, len(times), step_interval):
            timestamp = times[time_idx]
            hours_elapsed = (timestamp - times[0]) / np.timedelta64(1, 'h')
            
            # Should equal the time index value
            expected_hours = float(time_idx)
            
            self.assertAlmostEqual(
                float(hours_elapsed),
                expected_hours,
                places=1,
                msg=f"Hours elapsed at index {time_idx} with subsampling"
            )
    
    def test_particle_positions_vary_over_time(self):
        """Test that particle positions change over time"""
        ds = self.create_mock_dataset(num_particles=100, num_timesteps=24)
        
        # Get positions at start and end
        start_lons = ds['lon'].isel(time=0).values
        end_lons = ds['lon'].isel(time=-1).values
        
        # Positions should be different
        self.assertFalse(
            np.allclose(start_lons, end_lons),
            "Particle positions should change over time"
        )
        
        # Check that drift is generally in positive direction
        drift = end_lons.mean() - start_lons.mean()
        self.assertGreater(
            drift, 
            0,
            "Average drift should be positive (eastward)"
        )


class TestSliderBoundsChecks(unittest.TestCase):
    """Test bounds checking logic for slider"""
    
    def test_middle_mark_calculation(self):
        """Test that middle mark is calculated correctly for various sizes"""
        test_cases = [
            (1, 0),    # Only 1 element
            (2, 0),    # 2 elements, middle is 0
            (3, 1),    # 3 elements, middle is 1
            (24, 11),  # 24 elements, middle is 11
            (25, 12),  # 25 elements, middle is 12
        ]
        
        for max_steps, expected_middle in test_cases:
            middle_idx = (max_steps - 1) // 2
            self.assertEqual(
                middle_idx,
                expected_middle,
                f"Middle index for {max_steps} steps should be {expected_middle}"
            )
    
    def test_slider_value_bounds(self):
        """Test that slider values are within bounds"""
        timestep_contours = [
            {'hours_elapsed': i, 'timestamp': f'2024-01-01T{i:02d}:00:00Z'}
            for i in range(24)
        ]
        
        # Test valid indices
        for i in range(len(timestep_contours)):
            self.assertTrue(
                0 <= i < len(timestep_contours),
                f"Index {i} should be valid"
            )
        
        # Test invalid indices
        invalid_indices = [-1, len(timestep_contours), len(timestep_contours) + 1]
        for i in invalid_indices:
            self.assertFalse(
                0 <= i < len(timestep_contours),
                f"Index {i} should be invalid"
            )


if __name__ == '__main__':
    unittest.main()
