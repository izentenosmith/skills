# Weekly courier payouts

Owner: Courier Payments. Last reviewed 2026-10-03.

- **When:** every Friday at 06:00 UK time, for the week ending Sunday.
- **What:** `payouts-batch` reads every active courier's balance and `couriers.payout_account`, builds one
  Faster Payments file, signs it with the bank-issued key (HSM), and submits it. About 38,000 payments,
  £11.8m a week.
- **Which account:** whatever `couriers.payout_account` holds at 06:00. The batch has no notion of how
  or when that value last changed.
- **Reversal:** Faster Payments are final. A recall request goes to the receiving bank and succeeds only
  with that bank's cooperation; in 2025, 9% of our recall requests returned any money.
- **Failures:** a rejected payment (closed account, bad sort code) is retried the next Friday.
