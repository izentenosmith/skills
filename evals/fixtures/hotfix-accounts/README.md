# boxwise

Customer accounts for the Boxwise meal-kit shop: sign-up, sign-in and password reset.
The storefront calls these functions; `boxwise/web.py` is the thin HTTP layer in front of them.

## Development

Standard library only (Python 3.10+).

```bash
python3 -m unittest discover -s tests -p '*_test.py'
```

Tests live in `tests/`, one `<area>_test.py` per module, and build a fresh in-memory
database with `support.fresh_db()`.
