#!/usr/bin/env python3
"""
Test script for Drift Worker
Push test jobs to Redis queue for development and testing
"""

import redis
import json
import argparse
from datetime import datetime, timedelta


def push_test_job(redis_url: str, mission_id: str = None):
    """Push a test job to the Redis queue"""
    
    if mission_id is None:
        mission_id = f"test-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    
    # Connect to Redis
    r = redis.from_url(redis_url, decode_responses=True)
    
    # Create test job
    start_time = datetime.utcnow()
    job = {
        "mission_id": mission_id,
        "params": {
            "latitude": 60.0,  # North Sea
            "longitude": -3.0,
            "start_time": start_time.isoformat() + "Z",
            "duration_hours": 24,
            "num_particles": 100,
            "object_type": 1  # Person-in-water
        }
    }
    
    # Push to queue
    queue_name = 'drift_jobs'
    r.rpush(queue_name, json.dumps(job))
    
    print(f"✓ Pushed test job to queue '{queue_name}'")
    print(f"  Mission ID: {mission_id}")
    print(f"  Position: ({job['params']['latitude']}, {job['params']['longitude']})")
    print(f"  Start time: {job['params']['start_time']}")
    print(f"  Duration: {job['params']['duration_hours']} hours")
    print(f"  Particles: {job['params']['num_particles']}")
    
    return mission_id


def check_queue_length(redis_url: str):
    """Check how many jobs are in the queue"""
    r = redis.from_url(redis_url, decode_responses=True)
    queue_name = 'drift_jobs'
    length = r.llen(queue_name)
    print(f"Queue '{queue_name}' has {length} job(s)")
    return length


def clear_queue(redis_url: str):
    """Clear all jobs from the queue"""
    r = redis.from_url(redis_url, decode_responses=True)
    queue_name = 'drift_jobs'
    count = r.delete(queue_name)
    print(f"✓ Cleared queue '{queue_name}'")
    return count


def main():
    parser = argparse.ArgumentParser(description='Test Drift Worker')
    parser.add_argument('--redis-url', default='redis://localhost:6379/0',
                      help='Redis URL (default: redis://localhost:6379/0)')
    parser.add_argument('--mission-id', help='Mission ID (auto-generated if not provided)')
    parser.add_argument('--check', action='store_true', 
                      help='Check queue length')
    parser.add_argument('--clear', action='store_true',
                      help='Clear the queue')
    parser.add_argument('--multiple', type=int, metavar='N',
                      help='Push N test jobs')
    
    args = parser.parse_args()
    
    if args.check:
        check_queue_length(args.redis_url)
    elif args.clear:
        clear_queue(args.redis_url)
    elif args.multiple:
        for i in range(args.multiple):
            mission_id = f"test-batch-{i+1}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            push_test_job(args.redis_url, mission_id)
        print(f"\n✓ Pushed {args.multiple} test jobs")
    else:
        push_test_job(args.redis_url, args.mission_id)


if __name__ == '__main__':
    main()
