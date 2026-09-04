"""
Print a scratch Redis URL on the same server as REDIS_URL, on a different DB.

The inter-rater concurrency test takes real Redis locks. Running it against the
database the application is using would be a poor idea during a study, so the
test is pointed at a separate keyspace on the same instance instead — no extra
service to install, and nothing the app can see.

Override the index with RATER_TEST_REDIS_DB. Fails rather than guessing if the
application is already using that index.
"""

import os
import sys
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def _database_number(value: str, label: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise ValueError(f"{label} must be a non-negative integer") from error
    if number < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return number


def main() -> int:
    url = os.getenv("REDIS_URL", "")
    if not url:
        print("REDIS_URL is not set — source an env file first.", file=sys.stderr)
        return 1

    parsed = urlparse(url)
    if not parsed.hostname:
        print(f"REDIS_URL has no host: {url!r}", file=sys.stderr)
        return 1

    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    query_db = next((value for key, value in query_items if key == "db"), None)
    app_db_value = query_db if query_db is not None else parsed.path.lstrip("/") or "0"
    try:
        app_db = _database_number(app_db_value, "REDIS_URL database")
        scratch_db = _database_number(
            os.getenv("RATER_TEST_REDIS_DB", "15"),
            "RATER_TEST_REDIS_DB",
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    if app_db == scratch_db:
        print(
            f"The application is already using Redis DB {app_db}. "
            "Set RATER_TEST_REDIS_DB to a different index.",
            file=sys.stderr,
        )
        return 1

    scratch_query = urlencode(
        [(key, value) for key, value in query_items if key != "db"]
    )
    print(
        urlunparse(
            parsed._replace(path=f"/{scratch_db}", query=scratch_query)
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
