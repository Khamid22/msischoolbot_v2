"""Small authenticated staging load test for the granular academic read APIs.

Example:
  python scripts/benchmark_academic_api.py \
    --base-url https://staging.example.com \
    --session-cookie 'signed-cookie' --group-id 701 --users 200
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import date, timedelta

import httpx


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * fraction), len(ordered) - 1)
    return round(ordered[index], 1)


async def run(args) -> dict:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    paths = [
        "/api/v1/academic-director/academic/groups?limit=50",
        f"/api/v1/academic-director/academic/gradebook?group_id={args.group_id}&month={today:%Y-%m}&section=gradebook",
        (
            "/api/v1/academic-director/academic/timetable"
            f"?date_from={week_start.isoformat()}"
            f"&date_to={(week_start + timedelta(days=6)).isoformat()}"
            f"&group_id={args.group_id}"
        ),
    ]
    semaphore = asyncio.Semaphore(args.users)
    results: list[dict] = []
    headers = {"X-Requested-With": "XMLHttpRequest"}
    cookies = {"session": args.session_cookie}

    async with httpx.AsyncClient(
        base_url=args.base_url.rstrip("/"),
        headers=headers,
        cookies=cookies,
        timeout=args.timeout,
        follow_redirects=False,
    ) as client:
        async def request_once(index: int):
            path = paths[index % len(paths)]
            async with semaphore:
                started = time.perf_counter()
                try:
                    response = await client.get(path)
                    results.append(
                        {
                            "path": path.split("?", 1)[0],
                            "status": response.status_code,
                            "duration_ms": (time.perf_counter() - started) * 1000,
                            "bytes": len(response.content),
                        }
                    )
                except httpx.HTTPError:
                    results.append(
                        {
                            "path": path.split("?", 1)[0],
                            "status": 0,
                            "duration_ms": (time.perf_counter() - started) * 1000,
                            "bytes": 0,
                        }
                    )

        await asyncio.gather(
            *(request_once(index) for index in range(args.users * args.requests_per_user))
        )

    latencies = [row["duration_ms"] for row in results]
    failures = [row for row in results if row["status"] < 200 or row["status"] >= 400]
    by_path = {}
    for path in sorted({row["path"] for row in results}):
        rows = [row for row in results if row["path"] == path]
        durations = [row["duration_ms"] for row in rows]
        by_path[path] = {
            "requests": len(rows),
            "p50_ms": percentile(durations, 0.50),
            "p95_ms": percentile(durations, 0.95),
            "max_bytes": max((row["bytes"] for row in rows), default=0),
            "errors": sum(row["status"] < 200 or row["status"] >= 400 for row in rows),
        }
    return {
        "requests": len(results),
        "concurrent_users": args.users,
        "p50_ms": percentile(latencies, 0.50),
        "p95_ms": percentile(latencies, 0.95),
        "mean_ms": round(statistics.fmean(latencies), 1) if latencies else 0.0,
        "error_rate": round(len(failures) / len(results), 4) if results else 1.0,
        "by_path": by_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--session-cookie", required=True)
    parser.add_argument("--group-id", type=int, required=True)
    parser.add_argument("--users", type=int, default=200)
    parser.add_argument("--requests-per-user", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    report = asyncio.run(run(args))
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(report["error_rate"] >= 0.01 or report["p95_ms"] >= 750)


if __name__ == "__main__":
    raise SystemExit(main())
