package config

import (
	"bytes"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

// Config represents the top-level YAML configuration.
type Config struct {
	Global      GlobalConfig       `yaml:"global_config"`
	Connections []ConnectionConfig `yaml:"connections"`
	Queries     []QueryConfig      `yaml:"queries"`
	raw         map[string]any
}

// GlobalConfig contains settings that apply to the entire application.
type GlobalConfig struct {
	LogLevel            string `yaml:"log_level"`
	DefaultTimeInterval int    `yaml:"default_time_interval"`
	LogPath             string `yaml:"log_path"`
	Port                int    `yaml:"port"`
	QueueSize           int    `yaml:"queue_size"`
	LogConsole          *bool  `yaml:"log_console"`
}

// ConnectionConfig defines a DB2 connection target.
type ConnectionConfig struct {
	DBHost      string            `yaml:"db_host"`
	DBName      string            `yaml:"db_name"`
	DBPort      int               `yaml:"db_port"`
	DBUser      string            `yaml:"db_user"`
	DBPasswd    string            `yaml:"db_passwd"`
	DBUserVar   string            `yaml:"db_user_var"`
	DBPasswdVar string            `yaml:"db_passwd_var"`
	Tags        []string          `yaml:"tags"`
	ExtraLabels map[string]string `yaml:"extra_labels"`
}

// QueryConfig configures a query to execute against a connection.
type QueryConfig struct {
	Name          string        `yaml:"name"`
	RunsOn        []string      `yaml:"runs_on"`
	TimeInterval  int           `yaml:"time_interval"`
	Timeout       int           `yaml:"timeout"`
	Query         string        `yaml:"query"`
	Params        any           `yaml:"params"`
	MaxRows       int           `yaml:"max_rows"`
	MaxRetryDelay int           `yaml:"max_retry_delay"`
	Gauges        []GaugeConfig `yaml:"gauges"`
}

// GaugeConfig describes a Prometheus gauge derived from a query result.
type GaugeConfig struct {
	Name        string            `yaml:"name"`
	Desc        string            `yaml:"desc"`
	Col         int               `yaml:"col"`
	ExtraLabels map[string]string `yaml:"extra_labels"`
}

// Load reads a configuration file from disk, applies defaults, and validates it.
func Load(path string) (*Config, error) {
	if path == "" {
		return nil, errors.New("config path must not be empty")
	}
	content, err := os.ReadFile(filepath.Clean(path))
	if err != nil {
		return nil, fmt.Errorf("read config: %w", err)
	}

	var raw map[string]any
	if err := yaml.Unmarshal(content, &raw); err != nil {
		return nil, fmt.Errorf("parse config map: %w", err)
	}

	var cfg Config
	decoder := yaml.NewDecoder(bytes.NewReader(content))
	decoder.KnownFields(true)
	if err := decoder.Decode(&cfg); err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}
	cfg.raw = raw

	cfg.applyDefaults()
	if err := cfg.Validate(); err != nil {
		return nil, err
	}

	return &cfg, nil
}

// Validate ensures that the configuration contains the required settings.
func (c Config) Validate() error {
	if c.Global.DefaultTimeInterval <= 0 {
		return fmt.Errorf("global_config.default_time_interval must be positive")
	}
	if c.Global.Port <= 0 || c.Global.Port > 65535 {
		return fmt.Errorf("global_config.port must be between 1 and 65535")
	}
	if len(c.Connections) == 0 {
		return errors.New("at least one connection must be defined")
	}
	if len(c.Queries) == 0 {
		return errors.New("at least one query must be defined")
	}

	for i, conn := range c.Connections {
		if conn.DBHost == "" {
			return fmt.Errorf("connection[%d].db_host is required", i)
		}
		if conn.DBName == "" {
			return fmt.Errorf("connection[%d].db_name is required", i)
		}
		if conn.DBPort == 0 {
			return fmt.Errorf("connection[%d].db_port is required", i)
		}
	}

	for i, q := range c.Queries {
		if q.Name == "" {
			return fmt.Errorf("query[%d].name is required", i)
		}
		if strings.TrimSpace(q.Query) == "" {
			return fmt.Errorf("query[%d].query is required", i)
		}
		if len(q.Gauges) == 0 {
			return fmt.Errorf("query[%d] must define at least one gauge", i)
		}
		for j, g := range q.Gauges {
			if g.Name == "" {
				return fmt.Errorf("query[%d].gauges[%d].name is required", i, j)
			}
			if g.Col < 0 {
				return fmt.Errorf("query[%d].gauges[%d].col must be non-negative", i, j)
			}
		}
	}

	return nil
}

// DefaultTimeInterval returns the global default query interval as a duration.
func (c Config) DefaultTimeInterval() time.Duration {
	return time.Duration(c.Global.DefaultTimeInterval) * time.Second
}

// ConsoleLoggingEnabled reports whether log output should also be sent to stdout.
func (c Config) ConsoleLoggingEnabled() bool {
	if c.Global.LogConsole == nil {
		return true
	}
	return *c.Global.LogConsole
}

// Sanitize returns a copy of the raw configuration with password values masked.
func (c Config) Sanitize() map[string]any {
	return maskSensitive(c.raw)
}

// QueriesForConnection filters queries that should run on the given connection.
func (c Config) QueriesForConnection(conn ConnectionConfig) []QueryConfig {
	if len(c.Queries) == 0 {
		return nil
	}

	tags := map[string]struct{}{}
	for _, tag := range conn.Tags {
		if tag == "" {
			continue
		}
		tags[tag] = struct{}{}
	}

	var filtered []QueryConfig
	for _, q := range c.Queries {
		if len(q.RunsOn) == 0 {
			filtered = append(filtered, q)
			continue
		}
		if len(tags) == 0 {
			continue
		}
		if intersects(tags, q.RunsOn) {
			filtered = append(filtered, q)
		}
	}
	return filtered
}

// EffectiveInterval returns the interval for the query, falling back to the default when zero.
func (q QueryConfig) EffectiveInterval(defaultInterval time.Duration) time.Duration {
	if q.TimeInterval > 0 {
		return time.Duration(q.TimeInterval) * time.Second
	}
	return defaultInterval
}

func (c *Config) applyDefaults() {
	if c.Global.LogLevel == "" {
		c.Global.LogLevel = "INFO"
	} else {
		c.Global.LogLevel = strings.ToUpper(c.Global.LogLevel)
	}
	if c.Global.DefaultTimeInterval == 0 {
		c.Global.DefaultTimeInterval = 15
	}
	if c.Global.LogPath == "" {
		c.Global.LogPath = "logs"
	}
	if c.Global.Port == 0 {
		c.Global.Port = 9844
	}
	if c.Global.LogConsole == nil {
		defaultConsole := true
		c.Global.LogConsole = &defaultConsole
	}
	if c.Global.QueueSize < 0 {
		c.Global.QueueSize = 0
	}
}

func intersects(tags map[string]struct{}, runsOn []string) bool {
	for _, tag := range runsOn {
		if tag == "" {
			continue
		}
		if _, ok := tags[tag]; ok {
			return true
		}
	}
	return false
}

func maskSensitive(value any) map[string]any {
	sanitized := deepCopy(value)
	maskRecursive(sanitized)
	return sanitized
}

func deepCopy(value any) map[string]any {
	rawMap, ok := value.(map[string]any)
	if !ok {
		return map[string]any{}
	}

	out := make(map[string]any, len(rawMap))
	for k, v := range rawMap {
		out[k] = copyValue(v)
	}
	return out
}

func copyValue(v any) any {
	switch val := v.(type) {
	case map[string]any:
		m := make(map[string]any, len(val))
		for k, v := range val {
			m[k] = copyValue(v)
		}
		return m
	case []any:
		sliceCopy := make([]any, len(val))
		for i := range val {
			sliceCopy[i] = copyValue(val[i])
		}
		return sliceCopy
	default:
		return val
	}
}

func maskRecursive(v any) {
	switch val := v.(type) {
	case map[string]any:
		for k, vv := range val {
			if strings.Contains(strings.ToLower(k), "pass") {
				val[k] = "******"
			} else {
				maskRecursive(vv)
			}
		}
	case []any:
		for _, item := range val {
			maskRecursive(item)
		}
	}
}

// MaxConnectionLabels returns a sorted list of connection label keys used across all connections.
func (c Config) MaxConnectionLabels() []string {
	labelSet := map[string]struct{}{
		"dbhost": {},
		"dbport": {},
		"dbname": {},
	}
	for _, conn := range c.Connections {
		for key := range conn.ExtraLabels {
			if key == "" {
				continue
			}
			labelSet[key] = struct{}{}
		}
	}
	labels := make([]string, 0, len(labelSet))
	for label := range labelSet {
		labels = append(labels, label)
	}
	slices.Sort(labels)
	return labels
}
