package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog"

	"github.com/linkpulse/analytics-service/internal/services"
)

func NewRouter(analyticsService *services.AnalyticsService, wsHub *WebSocketHub, log zerolog.Logger) *gin.Engine {
	gin.SetMode(gin.ReleaseMode)
	router := gin.New()

	router.Use(gin.Recovery())
	router.Use(requestLogger(log))

	router.GET("/health", healthHandler)

	api := router.Group("/api/v1")
	{
		api.GET("/analytics/:url_code", getAnalyticsHandler(analyticsService))
		api.GET("/analytics/:url_code/hourly", getHourlyClicksHandler(analyticsService))
	}

	router.GET("/ws", wsHandler(wsHub))

	return router
}

func healthHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "ok",
		"service": "analytics-service",
	})
}

func getAnalyticsHandler(svc *services.AnalyticsService) gin.HandlerFunc {
	return func(c *gin.Context) {
		urlCode := c.Param("url_code")
		period := c.DefaultQuery("period", "24h")

		stats, err := svc.GetURLStats(c.Request.Context(), urlCode, period)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch analytics"})
			return
		}

		c.JSON(http.StatusOK, stats)
	}
}

func getHourlyClicksHandler(svc *services.AnalyticsService) gin.HandlerFunc {
	return func(c *gin.Context) {
		urlCode := c.Param("url_code")
		period := c.DefaultQuery("period", "24h")

		stats, err := svc.GetURLStats(c.Request.Context(), urlCode, period)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch analytics"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"url_code":       urlCode,
			"clicks_by_hour": stats.ClicksByHour,
		})
	}
}

func requestLogger(log zerolog.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Next()

		log.Info().
			Str("method", c.Request.Method).
			Str("path", c.Request.URL.Path).
			Int("status", c.Writer.Status()).
			Msg("request")
	}
}
