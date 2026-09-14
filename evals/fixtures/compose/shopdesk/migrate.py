"""Apply every SQL file in migrations/ in filename order.

Must run to completion before the API or a worker starts: both assume the
orders table exists.
"""
import pathlib
import sys

from shopdesk import db

MIGRATIONS = pathlib.Path(__file__).resolve().parent.parent / "migrations"


def main():
    with db.connect() as conn:
        for path in sorted(MIGRATIONS.glob("*.sql")):
            print(f"applying {path.name}", file=sys.stderr)
            conn.execute(path.read_text())
        conn.commit()


if __name__ == "__main__":
    main()
