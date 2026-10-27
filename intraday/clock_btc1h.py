"""Clock for the BTC 1h paper workflow (GitHub cron runs hours late). Same idea as clock/clock.py, separate so the
PAXG clock is untouched. Dispatches btc1h_paper.yml at minutes :03 and :25 every hour for `loop` minutes, then starts
the next clock. Usage: python -m intraday.clock_btc1h 340"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

REPO, TOKEN = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
MINUTES = (3, 25)


def dispatch(wf):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/actions/workflows/{wf}/dispatches",
        data=json.dumps({"ref": "main"}).encode(), method="POST",
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return f"{e.code} {e.read()[:200]!r}"
    except Exception as e:  # noqa: BLE001 - a failed dispatch must not kill the clock
        return f"error {e}"


def main():
    loop = int(sys.argv[1]) if len(sys.argv) > 1 else 340
    end, fired = time.time() + loop * 60, set()
    while time.time() < end:
        now = datetime.now(timezone.utc)
        key = (now.date(), now.hour, now.minute)
        if now.minute in MINUTES and key not in fired:
            fired.add(key)
            print(f"{now:%m-%d %H:%M} UTC btc1h_paper.yml -> {dispatch('btc1h_paper.yml')}", flush=True)
        time.sleep(15)
    print("next clock ->", dispatch("btc1h_clock.yml"), flush=True)


if __name__ == "__main__":
    main()
