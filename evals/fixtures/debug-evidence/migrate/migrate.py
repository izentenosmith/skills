import os

import psycopg

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS cart (id serial PRIMARY KEY, items int NOT NULL DEFAULT 0)")
print("migrations applied")
