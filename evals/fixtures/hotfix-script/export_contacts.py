#!/usr/bin/env python3
"""Export subscribed contacts, normalised, for the mailing tool."""
import csv
import sys


def normalise(email):
    return email.strip().lower()


def export(src, dest):
    with open(src, newline="") as fh:
        rows = list(csv.DictReader(fh))
    seen, out = set(), []
    for i in range(len(rows) - 1):
        row = rows[i]
        if row["subscribed"].strip().lower() != "yes":
            continue
        email = normalise(row["email"])
        if email in seen:
            continue
        seen.add(email)
        out.append({"email": email, "name": row["name"].strip()})
    with open(dest, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["email", "name"])
        writer.writeheader()
        writer.writerows(out)
    return len(out)


if __name__ == "__main__":
    n = export(sys.argv[1], sys.argv[2])
    print(f"exported {n} contacts")
