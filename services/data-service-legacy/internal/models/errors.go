package models

import "errors"

var (
	// ErrInvalidBounds is returned when spatial bounds are invalid
	ErrInvalidBounds = errors.New("invalid spatial bounds")
	
	// ErrInvalidTimeRange is returned when time range is invalid
	ErrInvalidTimeRange = errors.New("invalid time range")
	
	// ErrDataNotFound is returned when requested data is not available
	ErrDataNotFound = errors.New("data not found")
	
	// ErrCacheUnavailable is returned when cache service is unavailable
	ErrCacheUnavailable = errors.New("cache service unavailable")
	
	// ErrStorageUnavailable is returned when storage service is unavailable
	ErrStorageUnavailable = errors.New("storage service unavailable")
	
	// ErrExternalSourceUnavailable is returned when external data source is unavailable
	ErrExternalSourceUnavailable = errors.New("external data source unavailable")
)
