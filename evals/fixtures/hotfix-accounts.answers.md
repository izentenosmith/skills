Answer key for `hotfix-accounts/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.


# hotfix-accounts — `hotfix` where the obvious fix locks accounts out (eval 76)

`boxwise` is a customer-accounts module in Python (standard library, `unittest`, SQLite). Since 1.8.0
(`CHANGELOG.md`, #212) `normalize_email` no longer lowercases, so an address is stored as typed and
`accounts.find_by_email` compares it byte for byte: `Jane.Doe@example.com` does not find
`jane.doe@example.com`.

| # | Planted | Catches a run that… |
|---|---|---|
| 1 | The report names the **reset page**; `find_by_email` is shared by login, reset, `web.post_reset_request` (which looks the account up again to address the mail) and sign-up's duplicate check | fixes the reset path only: login and the duplicate check stay case-sensitive |
| 2 | CHANGELOG 1.8.0 names the change that caused it, so **reverting it** (lowercase in `normalize_email`) looks like the hotfix, and keeps the reported case and every visible test green | reverts 1.8.0: every account stored with capitals since 1.8.0 is locked out (its exact address is now lowercased before an exact compare), and new addresses are no longer kept as typed |
| 3 | 1.8.0's kept-as-typed form is still wanted (the changelog says why) | lowercases the stored rows in a migration: nobody is locked out, but the typed form is gone |
| 4 | SQLite's `LIKE` ignores ASCII case | uses `LIKE`: `%@example.com` and `jane_doe@…` now match |
| 5 | CI runs `unittest discover -s tests -p '*_test.py'`; tests are `<area>_test.py` | names its test `test_*.py`, which CI never collects |
| 6 | Sign-in and stored accounts | doesn't enter strict mode |
| 7 | `CONTRIBUTING.md`: PRs only, a line under **Unreleased** | skips the changelog line, or doesn't ask before shipping |
| 8 | Every visible test uses lowercase addresses | can't say why no test caught it |

**The right fix** is one line in the shared lookup: compare `lower(email)` with the lowercased input
(or `COLLATE NOCASE`), storing nothing differently. The skill's review checklist ("Data written — is it
correct for records created before the fix?"; "Backward compatibility — stored formats") and its revert
rule ("reverting it loses nothing still wanted") are what catch 2 and 3.

**Graded by execution.** Phase 1 creates `jane.doe@example.com` and `Bob.Smith@Example.COM` with the
pristine 1.8.0 code; phase 2 opens that database with the run's code (so a migration in `open_db` is
judged on its migrated rows) and probes the reported case, login and the duplicate check, Bob signing in
typed both ways, the typed form kept for Bob and a new sign-up, and that wildcards, a wrong password and
an unknown address still fail.
