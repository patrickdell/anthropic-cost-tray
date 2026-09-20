"""Print daily Anthropic API spend from the Admin API cost report.

Usage:
    set ANTHROPIC_ADMIN_KEY=sk-ant-admin...   (PowerShell: $env:ANTHROPIC_ADMIN_KEY="...")
    python cost_report.py [days]
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

URL = "https://api.anthropic.com/v1/organizations/cost_report"


def fetch(key, days):
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
    end = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    params = {"starting_at": start, "ending_at": end, "bucket_width": "1d",
              "limit": max(1, min(days + 1, 31)),
              "group_by[]": "description"}
    buckets, page = [], None
    while True:
        q = dict(params)
        if page:
            q["page"] = page
        req = urllib.request.Request(
            f"{URL}?{urllib.parse.urlencode(q)}",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.load(r)
        buckets += body["data"]
        if not body.get("has_more"):
            return buckets
        page = body["next_page"]


def main():
    key = os.environ.get("ANTHROPIC_ADMIN_KEY")
    if not key:
        sys.exit("Set ANTHROPIC_ADMIN_KEY first.")
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    per_day, per_model = {}, defaultdict(float)
    for b in fetch(key, days):
        total = 0.0
        for r in b["results"]:
            usd = float(r["amount"]) / 100  # amounts are in cents
            total += usd
            per_model[r.get("model") or "(other)"] += usd
        per_day[b["starting_at"][:10]] = total

    print("Daily spend (USD)")
    for d, v in sorted(per_day.items()):
        print(f"  {d}  {v:9.2f}  {'#' * int(v / max(per_day.values()) * 40) if v else ''}")
    print("\nBy model")
    for m, v in sorted(per_model.items(), key=lambda x: -x[1]):
        print(f"  {m:40} {v:9.2f}")
    print(f"\nTotal: ${sum(per_day.values()):.2f}")


if __name__ == "__main__":
    main()
