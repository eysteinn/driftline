package queue

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/redis/go-redis/v9"
)

var (
	// RedisClient is the global Redis client
	RedisClient *redis.Client
)

// Connect initializes the Redis client
func Connect() error {
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisURL = "redis://localhost:6379/0"
	}

	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return fmt.Errorf("failed to parse Redis URL: %w", err)
	}

	RedisClient = redis.NewClient(opts)

	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := RedisClient.Ping(ctx).Err(); err != nil {
		return fmt.Errorf("failed to connect to Redis: %w", err)
	}

	return nil
}

// Close closes the Redis connection
func Close() error {
	if RedisClient != nil {
		return RedisClient.Close()
	}
	return nil
}

// DriftJobParams represents the parameters for a drift simulation job
type DriftJobParams struct {
	Latitude      float64 `json:"latitude"`
	Longitude     float64 `json:"longitude"`
	StartTime     string  `json:"start_time"`
	DurationHours int     `json:"duration_hours"`
	NumParticles  int     `json:"num_particles"`
	ObjectType    int     `json:"object_type"`
	Backtracking  bool    `json:"backtracking"`
}

// DriftJob represents a drift simulation job
type DriftJob struct {
	MissionID string          `json:"mission_id"`
	Params    DriftJobParams  `json:"params"`
}

// EnqueueDriftJob adds a drift simulation job to the Redis queue
func EnqueueDriftJob(missionID string, params DriftJobParams) error {
	job := DriftJob{
		MissionID: missionID,
		Params:    params,
	}

	jobData, err := json.Marshal(job)
	if err != nil {
		return fmt.Errorf("failed to marshal job data: %w", err)
	}

	queueName := os.Getenv("QUEUE_NAME")
	if queueName == "" {
		queueName = "drift_jobs"
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := RedisClient.RPush(ctx, queueName, jobData).Err(); err != nil {
		return fmt.Errorf("failed to enqueue job: %w", err)
	}

	return nil
}
