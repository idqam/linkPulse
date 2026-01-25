package repository

import (
	"context"
	"encoding/json"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/linkpulse/analytics-service/internal/domain"
)

type ClickRepository struct {
	pool *pgxpool.Pool
}

func NewClickRepository(pool *pgxpool.Pool) *ClickRepository {
	return &ClickRepository{pool: pool}
}

func (r *ClickRepository) InsertClick(ctx context.Context, click *domain.ClickEvent) error {
	query := `
		INSERT INTO clicks (url_code, clicked_at, ip_hash, country, city, device_type, browser, os, referrer_domain)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
	`
	_, err := r.pool.Exec(ctx, query,
		click.URLCode,
		click.ClickedAt,
		click.IPHash,
		click.Country,
		click.City,
		click.DeviceType,
		click.Browser,
		click.OS,
		click.ReferrerDomain,
	)
	return err
}

func (r *ClickRepository) InsertSystemEvent(ctx context.Context, eventType string, userID *int64, data interface{}, occurredAt time.Time) error {
	dataJSON, err := json.Marshal(data)
	if err != nil {
		return err
	}

	query := `
		INSERT INTO system_events (event_type, user_id, data, occurred_at)
		VALUES ($1, $2, $3, $4)
	`
	_, err = r.pool.Exec(ctx, query, eventType, userID, dataJSON, occurredAt)
	return err
}

func (r *ClickRepository) GetClickStats(ctx context.Context, urlCode string, tr domain.TimeRange) (*domain.ClickStats, error) {
	stats := &domain.ClickStats{URLCode: urlCode}

	totalQuery := `SELECT COUNT(*) FROM clicks WHERE url_code = $1 AND clicked_at BETWEEN $2 AND $3`
	err := r.pool.QueryRow(ctx, totalQuery, urlCode, tr.Start, tr.End).Scan(&stats.TotalClicks)
	if err != nil {
		return nil, err
	}

	uniqueQuery := `SELECT COUNT(DISTINCT ip_hash) FROM clicks WHERE url_code = $1 AND clicked_at BETWEEN $2 AND $3`
	err = r.pool.QueryRow(ctx, uniqueQuery, urlCode, tr.Start, tr.End).Scan(&stats.UniqueVisitors)
	if err != nil {
		return nil, err
	}

	return stats, nil
}

func (r *ClickRepository) GetHourlyClicks(ctx context.Context, urlCode string, tr domain.TimeRange) ([]domain.HourlyClicks, error) {
	query := `
		SELECT time_bucket('1 hour', clicked_at) AS hour, COUNT(*) AS clicks
		FROM clicks
		WHERE url_code = $1 AND clicked_at BETWEEN $2 AND $3
		GROUP BY hour
		ORDER BY hour
	`
	rows, err := r.pool.Query(ctx, query, urlCode, tr.Start, tr.End)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []domain.HourlyClicks
	for rows.Next() {
		var hc domain.HourlyClicks
		if err := rows.Scan(&hc.Hour, &hc.Clicks); err != nil {
			return nil, err
		}
		result = append(result, hc)
	}
	return result, nil
}

func (r *ClickRepository) GetTopReferrers(ctx context.Context, urlCode string, tr domain.TimeRange, limit int) ([]domain.ReferrerCount, error) {
	query := `
		SELECT referrer_domain, COUNT(*) AS count
		FROM clicks
		WHERE url_code = $1 AND clicked_at BETWEEN $2 AND $3 AND referrer_domain != ''
		GROUP BY referrer_domain
		ORDER BY count DESC
		LIMIT $4
	`
	rows, err := r.pool.Query(ctx, query, urlCode, tr.Start, tr.End, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []domain.ReferrerCount
	for rows.Next() {
		var rc domain.ReferrerCount
		if err := rows.Scan(&rc.Domain, &rc.Count); err != nil {
			return nil, err
		}
		result = append(result, rc)
	}
	return result, nil
}

func (r *ClickRepository) GetDeviceBreakdown(ctx context.Context, urlCode string, tr domain.TimeRange) ([]domain.DeviceCount, error) {
	query := `
		SELECT device_type, COUNT(*) AS count
		FROM clicks
		WHERE url_code = $1 AND clicked_at BETWEEN $2 AND $3
		GROUP BY device_type
		ORDER BY count DESC
	`
	rows, err := r.pool.Query(ctx, query, urlCode, tr.Start, tr.End)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []domain.DeviceCount
	for rows.Next() {
		var dc domain.DeviceCount
		if err := rows.Scan(&dc.DeviceType, &dc.Count); err != nil {
			return nil, err
		}
		result = append(result, dc)
	}
	return result, nil
}

func (r *ClickRepository) GetGeoBreakdown(ctx context.Context, urlCode string, tr domain.TimeRange) ([]domain.GeoCount, error) {
	query := `
		SELECT country, COUNT(*) AS count
		FROM clicks
		WHERE url_code = $1 AND clicked_at BETWEEN $2 AND $3
		GROUP BY country
		ORDER BY count DESC
		LIMIT 10
	`
	rows, err := r.pool.Query(ctx, query, urlCode, tr.Start, tr.End)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []domain.GeoCount
	for rows.Next() {
		var gc domain.GeoCount
		if err := rows.Scan(&gc.Country, &gc.Count); err != nil {
			return nil, err
		}
		result = append(result, gc)
	}
	return result, nil
}

func NewPostgresConnection(connURL string) (*pgxpool.Pool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	config, err := pgxpool.ParseConfig(connURL)
	if err != nil {
		return nil, err
	}

	config.MaxConns = 10
	config.MinConns = 2

	pool, err := pgxpool.NewWithConfig(ctx, config)
	if err != nil {
		return nil, err
	}

	if err := pool.Ping(ctx); err != nil {
		return nil, err
	}

	return pool, nil
}
