# Changelog

## Unreleased

## 1.8.0 — 2026-11-17

- Account emails are kept exactly as the customer typed them, so support sees the address
  the customer knows; `normalize_email` no longer lowercases (#212).
- Password reset links expire after one hour instead of 24 (#209).

## 1.7.2 — 2026-10-30

- Sign-up rejects addresses without a dot in the domain (#201).

## 1.7.0 — 2026-10-02

- Password reset by email (#188).
