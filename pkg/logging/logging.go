package logging

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"gopkg.in/natefinch/lumberjack.v2"
)

// Config configures the logger outputs and formatting.
type Config struct {
	Directory  string
	Level      string
	Console    bool
	Filename   string
	ErrorFile  string
	MaxSizeMB  int
	MaxBackups int
	MaxAgeDays int
}

// Configure sets up slog with rotating file handlers and optional console output.
func Configure(cfg Config) (*slog.Logger, error) {
	applyDefaults(&cfg)

	if err := os.MkdirAll(cfg.Directory, 0o755); err != nil {
		return nil, fmt.Errorf("create log directory: %w", err)
	}

	level, err := parseLevel(cfg.Level)
	if err != nil {
		return nil, err
	}

	levelVar := &slog.LevelVar{}
	levelVar.Set(level)

	mainWriter := &lumberjack.Logger{
		Filename:   filepath.Join(cfg.Directory, cfg.Filename),
		MaxSize:    cfg.MaxSizeMB,
		MaxAge:     cfg.MaxAgeDays,
		MaxBackups: cfg.MaxBackups,
	}
	mainHandler := slog.NewTextHandler(mainWriter, &slog.HandlerOptions{Level: levelVar})

	errorLevelVar := &slog.LevelVar{}
	errorLevelVar.Set(slog.LevelError)
	errorWriter := &lumberjack.Logger{
		Filename:   filepath.Join(cfg.Directory, cfg.ErrorFile),
		MaxSize:    cfg.MaxSizeMB,
		MaxAge:     cfg.MaxAgeDays,
		MaxBackups: cfg.MaxBackups,
	}
	errorHandler := slog.NewTextHandler(errorWriter, &slog.HandlerOptions{Level: errorLevelVar})

	handlers := []slog.Handler{mainHandler, errorHandler}
	if cfg.Console {
		handlers = append(handlers, slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: levelVar}))
	}

	logger := slog.New(newMultiHandler(handlers...))
	slog.SetDefault(logger)
	return logger, nil
}

func applyDefaults(cfg *Config) {
	if cfg.Directory == "" {
		cfg.Directory = "logs"
	}
	if cfg.Level == "" {
		cfg.Level = "INFO"
	}
	if cfg.Filename == "" {
		cfg.Filename = "db2prom.log"
	}
	if cfg.ErrorFile == "" {
		cfg.ErrorFile = "db2prom.err"
	}
	if cfg.MaxSizeMB == 0 {
		cfg.MaxSizeMB = 10
	}
	if cfg.MaxBackups == 0 {
		cfg.MaxBackups = 5
	}
	if cfg.MaxAgeDays == 0 {
		cfg.MaxAgeDays = 28
	}
}

func parseLevel(level string) (slog.Level, error) {
	switch strings.ToUpper(level) {
	case "DEBUG":
		return slog.LevelDebug, nil
	case "INFO":
		return slog.LevelInfo, nil
	case "WARN", "WARNING":
		return slog.LevelWarn, nil
	case "ERROR", "ERR":
		return slog.LevelError, nil
	default:
		return slog.LevelInfo, fmt.Errorf("unknown log level %q", level)
	}
}

// multiHandler fans out log records to multiple handlers.
type multiHandler struct {
	handlers []slog.Handler
}

func newMultiHandler(handlers ...slog.Handler) slog.Handler {
	return &multiHandler{handlers: handlers}
}

// Handlers returns the underlying handlers; primarily used for tests or cleanup.
func (m *multiHandler) Handlers() []slog.Handler {
	return append([]slog.Handler(nil), m.handlers...)
}

func (m *multiHandler) Enabled(ctx context.Context, level slog.Level) bool {
	for _, h := range m.handlers {
		if h.Enabled(ctx, level) {
			return true
		}
	}
	return false
}

func (m *multiHandler) Handle(ctx context.Context, record slog.Record) error {
	var once sync.Once
	var firstErr error
	for _, h := range m.handlers {
		if !h.Enabled(ctx, record.Level) {
			continue
		}
		if err := h.Handle(ctx, record); err != nil {
			once.Do(func() {
				firstErr = err
			})
		}
	}
	return firstErr
}

func (m *multiHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	out := make([]slog.Handler, len(m.handlers))
	for i, h := range m.handlers {
		out[i] = h.WithAttrs(attrs)
	}
	return &multiHandler{handlers: out}
}

func (m *multiHandler) WithGroup(name string) slog.Handler {
	out := make([]slog.Handler, len(m.handlers))
	for i, h := range m.handlers {
		out[i] = h.WithGroup(name)
	}
	return &multiHandler{handlers: out}
}

// Close releases resources owned by handlers that implement io.Closer.
func Close(logger *slog.Logger) error {
	if logger == nil {
		return nil
	}
	handler := logger.Handler()
	return closeHandler(handler)
}

func closeHandler(h slog.Handler) error {
	type closer interface {
		Close() error
	}
	if c, ok := h.(closer); ok {
		return c.Close()
	}
	// Best-effort attempt to close nested handlers.
	type handlerWithChildren interface {
		Handlers() []slog.Handler
	}
	if composite, ok := h.(handlerWithChildren); ok {
		var errs []error
		for _, child := range composite.Handlers() {
			if err := closeHandler(child); err != nil {
				errs = append(errs, err)
			}
		}
		if len(errs) > 0 {
			return errors.Join(errs...)
		}
	}
	return nil
}
