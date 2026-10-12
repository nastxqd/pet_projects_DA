CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  level TEXT NOT NULL DEFAULT 'B1',
  variant TEXT NOT NULL DEFAULT 'A',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS onboarding (
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  goal TEXT NOT NULL,
  level TEXT NOT NULL,
  completed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  started_at TEXT NOT NULL,
  completed_at TEXT
);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  model_name TEXT,
  response_latency_ms INTEGER DEFAULT 0,
  token_cost REAL DEFAULT 0,
  task_success INTEGER DEFAULT 0,
  retry_count INTEGER DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS exercises (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_id TEXT,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  completed_at TEXT
);
CREATE TABLE IF NOT EXISTS ratings (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_id TEXT,
  rating INTEGER NOT NULL CHECK(rating IN (0,1)),
  feedback TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS subscriptions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  plan TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  cancelled_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_name TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  properties_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_name_time ON events(event_name, occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_messages_model ON messages(model_name);
