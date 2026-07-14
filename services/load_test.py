from __future__ import annotations

import argparse
import statistics
import time
from typing import Any

import requests

DEFAULT_FEATURES: dict[str, Any] = {
    "floor": 12,
    "kitchen_area": 13.8,
    "living_area": 41.2,
    "total_area": 62.0,
    "build_year": 2015,
    "latitude": 59.9343,
    "longitude": 30.3351,
    "ceiling_height": 2.85,
    "floors_total": 25,
    "area_per_room": 20.67,
    "is_first_floor": 0,
    "building_age": 10,
    "is_apartment": 1,
    "ce__building_type_int": 3,
    "building_age*latitude": 599.343,
    "build_year*building_age": 20150,
    "ce__building_type_int*has_elevator": 3,
    "latitude*longitude": 1817.031,
    "building_age*longitude": 303.351,
    "floors_total*longitude": 758.3775,
    "build_year*floors_total": 50375,
    "ceiling_height*latitude": 170.812,
    "build_year*rooms": 6045,
    "is_first_floor*total_area": 0.0,
    "rooms*total_area": 186.0,
    "build_year*living_area": 83018.0,
    "ceiling_height*longitude": 86.455,
    "ceiling_height*floors_total": 71.25,
    "has_elevator*is_first_floor": 0,
}


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * fraction), len(ordered) - 1)
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description="Send valid prediction requests to the ML service")
    parser.add_argument("--url", default="http://127.0.0.1:8002/predict")
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    if args.requests < 1:
        raise SystemExit("--requests must be positive")

    latencies: list[float] = []
    failures = 0

    with requests.Session() as session:
        for index in range(args.requests):
            payload = {
                "user_id": index + 1,
                "features": DEFAULT_FEATURES,
            }
            started = time.perf_counter()

            try:
                response = session.post(args.url, json=payload, timeout=args.timeout)
                latency = time.perf_counter() - started
                response.raise_for_status()
                latencies.append(latency)
                print(f"{index + 1:03d} status={response.status_code} latency={latency:.4f}s")
            except requests.RequestException as exc:
                failures += 1
                print(f"{index + 1:03d} failed: {exc}")

            if index + 1 < args.requests:
                time.sleep(args.delay)

    if latencies:
        print(
            "summary "
            f"success={len(latencies)} failures={failures} "
            f"mean={statistics.fmean(latencies):.4f}s "
            f"p50={percentile(latencies, 0.50):.4f}s "
            f"p95={percentile(latencies, 0.95):.4f}s"
        )

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
