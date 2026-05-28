"""Send a test ZeroDivisionError to Sentry so autopilot has an active issue."""
import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def _get_dsn() -> str:
    org = os.environ["SENTRY_ORG"]
    project = os.environ["SENTRY_PROJECT"]
    token = os.environ["SENTRY_AUTH_TOKEN"]
    url = f"https://sentry.io/api/0/projects/{org}/{project}/keys/"
    resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    resp.raise_for_status()
    keys = resp.json()
    if not keys:
        raise RuntimeError("No Sentry DSN keys found for project.")
    return keys[0]["dsn"]["public"]


def main():
    print("Fetching Sentry DSN...")
    dsn = _get_dsn()
    print("Sending test exception (ZeroDivisionError in app.py)...")

    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=0.0,
        environment="cortexsre-test",
    )

    def calculate_product_rating(reviews):
        total_score = sum(review["score"] for review in reviews)
        count = len(reviews)
        return total_score / count  # noqa: intentional demo bug

    try:
        calculate_product_rating([])
    except ZeroDivisionError:
        event_id = sentry_sdk.capture_exception()
        sentry_sdk.flush(timeout=10)
        print(f"Done. Event sent to Sentry (event_id={event_id}).")
        print("Wait ~10s, then run: python check_connectivity.py")


if __name__ == "__main__":
    main()
