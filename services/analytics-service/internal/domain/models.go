package domain

import "time"

type ClickEvent struct {
	ID             int64     `json:"id"`
	URLCode        string    `json:"url_code"`
	ClickedAt      time.Time `json:"clicked_at"`
	IPHash         string    `json:"ip_hash"`
	Country        string    `json:"country"`
	City           string    `json:"city"`
	DeviceType     string    `json:"device_type"`
	Browser        string    `json:"browser"`
	OS             string    `json:"os"`
	ReferrerDomain string    `json:"referrer_domain"`
}

type ClickStats struct {
	URLCode          string          `json:"url_code"`
	TotalClicks      int64           `json:"total_clicks"`
	UniqueVisitors   int64           `json:"unique_visitors"`
	ClicksByHour     []HourlyClicks  `json:"clicks_by_hour"`
	TopReferrers     []ReferrerCount `json:"top_referrers"`
	DeviceBreakdown  []DeviceCount   `json:"device_breakdown"`
	BrowserBreakdown []BrowserCount  `json:"browser_breakdown"`
	GeoBreakdown     []GeoCount      `json:"geo_breakdown"`
}

type HourlyClicks struct {
	Hour   time.Time `json:"hour"`
	Clicks int64     `json:"clicks"`
}

type ReferrerCount struct {
	Domain string `json:"domain"`
	Count  int64  `json:"count"`
}

type DeviceCount struct {
	DeviceType string `json:"device_type"`
	Count      int64  `json:"count"`
}

type BrowserCount struct {
	Browser string `json:"browser"`
	Count   int64  `json:"count"`
}

type GeoCount struct {
	Country string `json:"country"`
	Count   int64  `json:"count"`
}

type TimeRange struct {
	Start time.Time
	End   time.Time
}

func Last24Hours() TimeRange {
	now := time.Now().UTC()
	return TimeRange{
		Start: now.Add(-24 * time.Hour),
		End:   now,
	}
}

func Last7Days() TimeRange {
	now := time.Now().UTC()
	return TimeRange{
		Start: now.Add(-7 * 24 * time.Hour),
		End:   now,
	}
}

func Last30Days() TimeRange {
	now := time.Now().UTC()
	return TimeRange{
		Start: now.Add(-30 * 24 * time.Hour),
		End:   now,
	}
}
