import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";

// Shipped next to dist/, read at startup.
const MIGRATIONS = path.join(__dirname, "..", "migrations");

export function openDb() {
  const file = process.env.DATABASE_PATH ?? path.join(process.cwd(), "data", "invoicer.db");
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const db = new Database(file);
  db.pragma("journal_mode = WAL");
  db.exec("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)");
  const done = new Set(db.prepare("SELECT name FROM schema_migrations").pluck().all());
  for (const f of fs.readdirSync(MIGRATIONS).filter((f) => f.endsWith(".sql")).sort()) {
    if (done.has(f)) continue;
    db.exec(fs.readFileSync(path.join(MIGRATIONS, f), "utf8"));
    db.prepare("INSERT INTO schema_migrations (name) VALUES (?)").run(f);
  }
  return db;
}
