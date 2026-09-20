# Audit

Scope: `tray.py`, `cost_report.py` (~150 lines). Reviewed by reading the code and exercising the API calls
against a real org. Not an independent security assessment.

## Fixed
| Issue | Fix |
|---|---|
| HTTP requests had no timeout, so a stalled connection would hang the poll thread forever | 30 s timeout |
| Single-instance guard used a localhost TCP port; another process holding the port would silently block the app | Named Windows mutex |
| Range starting in the current UTC day was rejected by the API (400) | Query from yesterday, filter to today's bucket |
| Tiny, unreadable tray text | Full-tile icon, ≤3 large characters |
| Admin API key stored in plaintext in `%APPDATA%` | Windows Credential Manager via `keyring`; legacy key file is migrated and deleted |

## Open findings
| Severity | Finding | Notes |
|---|---|---|
| **Medium** | Admin keys cannot be scoped to read-only | Inherent to Anthropic's Admin API; a leaked key can manage the org. Documented in README. |
| Medium | Cost unit (cents) is taken from docs, not independently verified | Confirm against the Console before trusting the number. |
| Low | Credential Manager entries are readable by any process running as the same Windows user | Inherent to per-user credential stores. |
| Low | Unsigned exe triggers SmartScreen; no update mechanism or hash published | Build from source if in doubt. |
| Low | Spend is by UTC day, not local day | API limitation (1d buckets only). |
| Low | Errors surface only in the tooltip (truncated to 127 chars) | No logging. |
| Low | Cancelling the key prompt exits silently | |
| Info | Dependencies are unpinned (`pystray`, `Pillow`, `pyinstaller`) | Pin versions / add a lockfile for reproducible builds. |
| Info | No tests | Icon colour/text logic and bucket filtering are easy to unit test. |

## Checked and fine
- Key is only sent to `api.anthropic.com` over HTTPS, in the `x-api-key` header, never in a URL or log.
- No secrets or personal information in the repo (checked source, docs and commit author); `.gitignore` excludes key files and build output.
- Pagination follows `next_page` until `has_more` is false.
- No shell execution, no `eval`, no untrusted deserialization beyond `json.load` of the API response.
