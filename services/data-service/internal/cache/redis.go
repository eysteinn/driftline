package cache

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/go-redis/redis/v8"
)

// Service provides caching functionality using Redis
type Service struct {
	client *redis.Client
	ttl    time.Duration
}

// NewService creates a new cache service
func NewService(redisURL string, ttl time.Duration) (*Service, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse redis URL: %w", err)
	}

	client := redis.NewClient(opts)
	
	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to redis: %w", err)
	}

	return &Service{
		client: client,
		ttl:    ttl,
	}, nil
}

// Get retrieves a value from cache
func (s *Service) Get(ctx context.Context, key string) (string, error) {
	val, err := s.client.Get(ctx, key).Result()
	if err == redis.Nil {
		return "", nil // Cache miss
	}
	if err != nil {
		return "", err
	}
	return val, nil
}

// Set stores a value in cache with TTL
func (s *Service) Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error {
	if ttl == 0 {
		ttl = s.ttl
	}
	
	var data []byte
	var err error
	
	switch v := value.(type) {
	case string:
		data = []byte(v)
	case []byte:
		data = v
	default:
		data, err = json.Marshal(value)
		if err != nil {
			return fmt.Errorf("failed to marshal value: %w", err)
		}
	}
	
	return s.client.Set(ctx, key, data, ttl).Err()
}

// Delete removes a value from cache
func (s *Service) Delete(ctx context.Context, key string) error {
	return s.client.Del(ctx, key).Err()
}

// Exists checks if a key exists in cache
func (s *Service) Exists(ctx context.Context, key string) (bool, error) {
	n, err := s.client.Exists(ctx, key).Result()
	if err != nil {
		return false, err
	}
	return n > 0, nil
}

// Close closes the Redis connection
func (s *Service) Close() error {
	return s.client.Close()
}

// GenerateDataCacheKey generates a cache key for environmental data requests
func GenerateDataCacheKey(dataType, bounds, timeRange string) string {
	return fmt.Sprintf("data:%s:%s:%s", dataType, bounds, timeRange)
}
