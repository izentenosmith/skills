CREATE TABLE IF NOT EXISTS invoices (
  id         TEXT PRIMARY KEY,
  customer   TEXT NOT NULL,
  lines_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
