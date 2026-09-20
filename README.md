# Anthropic Cost Tray

A Windows system-tray icon showing today's Anthropic API spend. The icon shifts green → yellow → red as
spend approaches a daily budget (default $5). Hover for the exact figure.

Data comes from the Anthropic Admin API cost report (`GET /v1/organizations/cost_report`).
Standard library + `pystray` + `Pillow`; no third-party network calls.

## Run

```powershell
pip install pystray pillow keyring
python tray.py            # prompts once for your Admin API key
```

Settings (environment variables): `ANTHROPIC_ADMIN_KEY`, `BUDGET_USD` (default 5), `POLL_SECONDS` (default 300).

Build a single exe: `pip install pyinstaller` then
`python -m PyInstaller --onefile --noconsole --hidden-import keyring.backends.Windows --name AnthropicCost tray.py`.

`python cost_report.py [days]` prints a daily/by-model table in the terminal.

## Read this before using

- **Admin API keys are powerful.** They can manage org members, workspaces and API keys, and cannot be
  scoped down to read-only cost data. Treat the key like a password.
- **The key is stored in Windows Credential Manager** (service `anthropic-cost-tray`), or read from
  `ANTHROPIC_ADMIN_KEY` if set. It is encrypted for your Windows user, but any program running as you can
  still read it. To forget it: Credential Manager → Windows Credentials → remove `anthropic-cost-tray`.
- **"Today" is a UTC day**, because the API only returns whole UTC-day buckets.
- **Amounts are treated as USD.** The API docs describe them as cents, but a real org's figures matched the
  Console in dollars, so no conversion is applied. Compare against your own Console before trusting it.
- The exe is unsigned, so SmartScreen will warn. Build it yourself if you don't trust a binary.

See [AUDIT.md](AUDIT.md) for the security/quality review.
