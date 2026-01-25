package logger

import (
	"os"
	"time"

	"github.com/rs/zerolog"
)

func New() zerolog.Logger {
	output := zerolog.ConsoleWriter{
		Out:        os.Stdout,
		TimeFormat: time.RFC3339,
	}

	return zerolog.New(output).
		With().
		Timestamp().
		Caller().
		Logger()
}
