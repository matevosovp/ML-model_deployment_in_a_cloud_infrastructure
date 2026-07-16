from __future__ import annotations

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import httpx2

from ml_service.schemas import EXAMPLE_FEATURES

DEFAULT_FEATURES = EXAMPLE_FEATURES


@dataclass(frozen=True, slots=True)
class RequestResult:
    index: int
    latency: float
    error: str | None = None


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * fraction), len(ordered) - 1)
    return ordered[index]


def send_request(client: httpx2.Client, url: str, index: int) -> RequestResult:
    payload = {"user_id": index + 1, "features": DEFAULT_FEATURES}
    started = time.perf_counter()

    try:
        response = client.post(url, json=payload)
        latency = time.perf_counter() - started
        response.raise_for_status()
        body: dict[str, Any] = response.json()
        if body.get("user_id") != index + 1 or not isinstance(
            body.get("prediction"), (int, float)
        ):
            raise ValueError("response does not match PredictResponse")
        return RequestResult(index=index, latency=latency)
    except (httpx2.HTTPError, ValueError) as exc:
        return RequestResult(
            index=index,
            latency=time.perf_counter() - started,
            error=str(exc),
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send contract-valid prediction requests to the ML service"
    )
    parser.add_argument("--url", default="http://127.0.0.1:8002/predict")
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    if args.requests < 1:
        raise SystemExit("--requests must be positive")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be positive")

    results: list[RequestResult] = []
    limits = httpx2.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    with httpx2.Client(timeout=args.timeout, limits=limits) as client:
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = [
                executor.submit(send_request, client, args.url, index)
                for index in range(args.requests)
            ]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                if result.error:
                    print(f"{result.index + 1:03d} failed: {result.error}")
                else:
                    print(f"{result.index + 1:03d} status=200 latency={result.latency:.4f}s")

    latencies = [result.latency for result in results if result.error is None]
    failures = len(results) - len(latencies)
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
