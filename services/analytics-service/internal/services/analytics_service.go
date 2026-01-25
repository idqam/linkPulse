package services

import (
	"context"

	"github.com/linkpulse/analytics-service/internal/domain"
	"github.com/linkpulse/analytics-service/internal/repository"
)

type AnalyticsService struct {
	clickRepo *repository.ClickRepository
}

func NewAnalyticsService(clickRepo *repository.ClickRepository) *AnalyticsService {
	return &AnalyticsService{clickRepo: clickRepo}
}

func (s *AnalyticsService) GetURLStats(ctx context.Context, urlCode string, period string) (*domain.ClickStats, error) {
	var tr domain.TimeRange
	switch period {
	case "7d":
		tr = domain.Last7Days()
	case "30d":
		tr = domain.Last30Days()
	default:
		tr = domain.Last24Hours()
	}

	stats, err := s.clickRepo.GetClickStats(ctx, urlCode, tr)
	if err != nil {
		return nil, err
	}

	hourlyClicks, err := s.clickRepo.GetHourlyClicks(ctx, urlCode, tr)
	if err != nil {
		return nil, err
	}
	stats.ClicksByHour = hourlyClicks

	topReferrers, err := s.clickRepo.GetTopReferrers(ctx, urlCode, tr, 10)
	if err != nil {
		return nil, err
	}
	stats.TopReferrers = topReferrers

	deviceBreakdown, err := s.clickRepo.GetDeviceBreakdown(ctx, urlCode, tr)
	if err != nil {
		return nil, err
	}
	stats.DeviceBreakdown = deviceBreakdown

	geoBreakdown, err := s.clickRepo.GetGeoBreakdown(ctx, urlCode, tr)
	if err != nil {
		return nil, err
	}
	stats.GeoBreakdown = geoBreakdown

	return stats, nil
}

func (s *AnalyticsService) RecordClick(ctx context.Context, click *domain.ClickEvent) error {
	return s.clickRepo.InsertClick(ctx, click)
}
