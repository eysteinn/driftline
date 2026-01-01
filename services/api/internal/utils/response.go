package utils

import "github.com/gin-gonic/gin"

// SuccessResponse sends a standardized success response
func SuccessResponse(c *gin.Context, statusCode int, data interface{}) {
	c.JSON(statusCode, gin.H{
		"data": data,
	})
}

// ErrorResponse sends a standardized error response
func ErrorResponse(c *gin.Context, statusCode int, message string) {
	c.JSON(statusCode, gin.H{
		"error":   message,
		"message": message,
	})
}

// PaginatedResponse sends a paginated response
func PaginatedResponse(c *gin.Context, data interface{}, total, page, perPage int) {
	c.JSON(200, gin.H{
		"data":    data,
		"total":   total,
		"page":    page,
		"perPage": perPage,
	})
}
