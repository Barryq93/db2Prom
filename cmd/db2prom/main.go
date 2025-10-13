package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"db2prom/pkg/config"
	"db2prom/pkg/logging"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var configPath = flag.String("config", "config.yaml", "Path to the configuration file")

func main() {
	flag.Parse()
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	if err := run(ctx); err != nil {
		fmt.Fprintf(os.Stderr, "db2prom: %v\n", err)
		os.Exit(1)
	}
}

func run(ctx context.Context) error {
	if configPath == nil || *configPath == "" {
		return errors.New("a configuration file path is required")
	}

	cfg, err := config.Load(*configPath)
	if err != nil {
		return err
	}

	logger, err := logging.Configure(logging.Config{
		Directory: cfg.Global.LogPath,
		Level:     cfg.Global.LogLevel,
		Console:   cfg.ConsoleLoggingEnabled(),
	})
	if err != nil {
		return err
	}

	logger.Info("configuration loaded", "config", cfg.Sanitize())
	logger.Info("max connection labels computed", "labels", cfg.MaxConnectionLabels())

	exp := newExporter(cfg.Global.Port)
	if err := exp.Start(); err != nil {
		return fmt.Errorf("start exporter: %w", err)
	}
	defer func() {
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := exp.Shutdown(shutdownCtx); err != nil && !errors.Is(err, http.ErrServerClosed) {
			slog.Error("error shutting down exporter", "error", err)
		}
	}()

	workerCtx, cancelWorkers := context.WithCancel(ctx)
	defer cancelWorkers()

	var wg sync.WaitGroup
	defaultInterval := cfg.DefaultTimeInterval()
	for _, conn := range cfg.Connections {
		connection := conn
		queries := cfg.QueriesForConnection(connection)
		if len(queries) == 0 {
			logger.Warn("no queries configured for connection; skipping", "db_host", connection.DBHost, "db_name", connection.DBName)
			continue
		}
		wg.Add(1)
		go func() {
			defer wg.Done()
			runConnection(workerCtx, connection, queries, defaultInterval)
		}()
	}

	<-ctx.Done()
	cancelWorkers()
	wg.Wait()

	logger.Info("shutdown complete")
	return nil
}

func runConnection(ctx context.Context, conn config.ConnectionConfig, queries []config.QueryConfig, defaultInterval time.Duration) {
	connLogger := slog.Default().With(
		"db_host", conn.DBHost,
		"db_name", conn.DBName,
		"db_port", conn.DBPort,
	)
	connLogger.Info("starting connection worker", "queries", len(queries))

	var wg sync.WaitGroup
	for _, query := range queries {
		q := query
		interval := q.EffectiveInterval(defaultInterval)
		if interval <= 0 {
			interval = defaultInterval
		}
		wg.Add(1)
		go func() {
			defer wg.Done()
			runQueryLoop(ctx, connLogger, q, interval)
		}()
	}

	<-ctx.Done()
	wg.Wait()
	connLogger.Info("connection worker stopped")
}

func runQueryLoop(ctx context.Context, connLogger *slog.Logger, query config.QueryConfig, interval time.Duration) {
	logger := connLogger.With("query", query.Name, "interval", interval.String())
	logger.Info("starting query loop")
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			logger.Info("stopping query loop")
			return
		case <-ticker.C:
			logger.Debug("executing query", "gauges", len(query.Gauges))
		}
	}
}

type exporter struct {
	server *http.Server
}

func newExporter(port int) *exporter {
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())

	return &exporter{
		server: &http.Server{
			Addr:    fmt.Sprintf(":%d", port),
			Handler: mux,
		},
	}
}

func (e *exporter) Start() error {
	listener, err := net.Listen("tcp", e.server.Addr)
	if err != nil {
		return err
	}

	go func() {
		if err := e.server.Serve(listener); err != nil && !errors.Is(err, http.ErrServerClosed) {
			slog.Error("exporter server error", "error", err)
		}
	}()

	return nil
}

func (e *exporter) Shutdown(ctx context.Context) error {
	return e.server.Shutdown(ctx)
}
