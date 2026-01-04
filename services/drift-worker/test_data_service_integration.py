#!/usr/bin/env python3
"""
Integration test for drift-worker and data-service connection
This test verifies that the drift-worker can successfully connect to and fetch data from data-service
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta

def test_data_service_connectivity():
    """Test that data-service is accessible"""
    data_service_url = os.getenv('DATA_SERVICE_URL', 'http://localhost:8000')
    
    print(f"Testing data-service connectivity at {data_service_url}...")
    
    try:
        # Test health endpoint
        response = requests.get(f"{data_service_url}/health", timeout=5)
        if response.status_code == 200:
            print("✓ Data-service health check passed")
            health_data = response.json()
            print(f"  Service: {health_data.get('service')}")
            print(f"  Status: {health_data.get('status')}")
            return True
        else:
            print(f"✗ Data-service health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to data-service: {e}")
        return False

def test_data_service_api():
    """Test that data-service API endpoints work"""
    data_service_url = os.getenv('DATA_SERVICE_URL', 'http://localhost:8000')
    
    print(f"\nTesting data-service API endpoints...")
    
    # Test parameters
    params = {
        'min_lat': 58.0,
        'max_lat': 62.0,
        'min_lon': -5.0,
        'max_lon': -1.0,
        'start_time': datetime.utcnow().isoformat() + 'Z',
        'end_time': (datetime.utcnow() + timedelta(hours=24)).isoformat() + 'Z'
    }
    
    endpoints = [
        'ocean-currents',
        'wind',
        'waves'
    ]
    
    results = {}
    for endpoint in endpoints:
        try:
            url = f"{data_service_url}/v1/data/{endpoint}"
            print(f"\n  Testing {endpoint}...")
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ {endpoint} endpoint responded")
                print(f"    Data type: {data.get('data_type')}")
                print(f"    Cache hit: {data.get('cache_hit')}")
                print(f"    File path: {data.get('file_path', 'N/A')}")
                results[endpoint] = True
            else:
                print(f"  ✗ {endpoint} failed: HTTP {response.status_code}")
                results[endpoint] = False
                
        except Exception as e:
            print(f"  ✗ {endpoint} error: {e}")
            results[endpoint] = False
    
    return all(results.values())

def test_worker_configuration():
    """Test that worker configuration includes data-service URL"""
    print("\nTesting worker configuration...")
    
    # Check config file
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from config import DEFAULT_DATA_SERVICE_URL, DATA_SERVICE_TIMEOUT, SPATIAL_BUFFER
        print(f"✓ Configuration loaded successfully")
        print(f"  DEFAULT_DATA_SERVICE_URL: {DEFAULT_DATA_SERVICE_URL}")
        print(f"  DATA_SERVICE_TIMEOUT: {DATA_SERVICE_TIMEOUT}s")
        print(f"  SPATIAL_BUFFER: {SPATIAL_BUFFER}°")
        return True
    except ImportError as e:
        print(f"✗ Failed to import configuration: {e}")
        return False

def main():
    """Run all integration tests"""
    print("=" * 60)
    print("Drift Worker <-> Data Service Integration Test")
    print("=" * 60)
    
    tests = [
        ("Worker Configuration", test_worker_configuration),
        ("Data Service Connectivity", test_data_service_connectivity),
        ("Data Service API", test_data_service_api),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
    else:
        print("✗ Some tests failed")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
