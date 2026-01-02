package models

import (
	"testing"
	"time"
)

func TestDataRequestValidate(t *testing.T) {
	tests := []struct {
		name    string
		req     *DataRequest
		wantErr bool
	}{
		{
			name: "valid request",
			req: &DataRequest{
				DataType:  DataTypeOceanCurrents,
				MinLat:    60.0,
				MaxLat:    70.0,
				MinLon:    -20.0,
				MaxLon:    -10.0,
				StartTime: time.Now(),
				EndTime:   time.Now().Add(24 * time.Hour),
			},
			wantErr: false,
		},
		{
			name: "invalid bounds - minLat >= maxLat",
			req: &DataRequest{
				DataType:  DataTypeOceanCurrents,
				MinLat:    70.0,
				MaxLat:    60.0,
				MinLon:    -20.0,
				MaxLon:    -10.0,
				StartTime: time.Now(),
				EndTime:   time.Now().Add(24 * time.Hour),
			},
			wantErr: true,
		},
		{
			name: "invalid bounds - minLon >= maxLon",
			req: &DataRequest{
				DataType:  DataTypeOceanCurrents,
				MinLat:    60.0,
				MaxLat:    70.0,
				MinLon:    -10.0,
				MaxLon:    -20.0,
				StartTime: time.Now(),
				EndTime:   time.Now().Add(24 * time.Hour),
			},
			wantErr: true,
		},
		{
			name: "invalid time range - start after end",
			req: &DataRequest{
				DataType:  DataTypeOceanCurrents,
				MinLat:    60.0,
				MaxLat:    70.0,
				MinLon:    -20.0,
				MaxLon:    -10.0,
				StartTime: time.Now().Add(24 * time.Hour),
				EndTime:   time.Now(),
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.req.Validate()
			if (err != nil) != tt.wantErr {
				t.Errorf("DataRequest.Validate() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestDataType(t *testing.T) {
	tests := []struct {
		name     string
		dataType DataType
		want     string
	}{
		{"ocean currents", DataTypeOceanCurrents, "ocean_currents"},
		{"wind", DataTypeWind, "wind"},
		{"waves", DataTypeWaves, "waves"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if string(tt.dataType) != tt.want {
				t.Errorf("DataType = %v, want %v", tt.dataType, tt.want)
			}
		})
	}
}
