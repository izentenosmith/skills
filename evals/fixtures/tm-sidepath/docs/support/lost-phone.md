# Playbook: courier has lost their phone or changed number

Owner: Courier Operations · Used by: Tier-1 (outsourced partner) · Last updated 2026-09-02

**When:** a courier calls or chats to say they've lost their phone or changed number and can't
receive codes. About 1,300 contacts a month.

1. **Verify identity.** Ask for the courier ID, date of birth and home postcode. All three must match.
2. In the Ops Console, open the courier → **Edit profile**. Update the phone number to the new one.
3. If the courier also asks to update their bank details (common, because the app asks for an SMS code
   they can't receive), update **Payout account** on the same Edit profile screen and save.
4. Tell the courier the change is done.
5. Close the ticket with the tag `lost-phone`.

**Console down?** Tier-2 can make the same change directly:

```
curl -X PATCH https://accounts.internal.parcelry.test/internal/couriers/{courierId} \
  -H "X-Ops-Token: ops-eval-fake-token-0079" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+44...", "payoutAccount": {"accountNumber": "...", "sortCode": "...", "holderName": "..."}}'
```

**Tips:** the courier ID is printed on the courier's delivery bag and on the order receipt customers
see, so couriers can usually read it out.
