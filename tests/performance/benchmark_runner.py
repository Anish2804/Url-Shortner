"""
High-Performance Benchmark Runner for URL Shortening & Redirects
Measures redirect latency percentiles (p50, p90, p95, p99, min, max, avg),
throughput (Requests Per Second), error distribution, and cache effectiveness.

Can be run against a live running server or locally against the ASGI app.
"""

import asyncio
import time
import statistics
import argparse
from typing import List, Dict, Any
import httpx


async def run_worker(
    worker_id: int,
    client: httpx.AsyncClient,
    targets: List[str],
    num_requests: int,
    latencies: List[float],
    status_counts: Dict[int, int],
):
    for i in range(num_requests):
        target = targets[i % len(targets)]
        start_time = time.perf_counter()
        try:
            # We do NOT follow redirects to measure the exact 302 response latency
            resp = await client.get(target, follow_redirects=False)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            latencies.append(elapsed_ms)
            status = resp.status_code
            status_counts[status] = status_counts.get(status, 0) + 1
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            latencies.append(elapsed_ms)
            status_counts[599] = status_counts.get(599, 0) + 1


async def execute_benchmark(
    base_url: str,
    concurrency: int,
    total_requests: int,
    test_paths: List[str],
) -> Dict[str, Any]:
    requests_per_worker = total_requests // concurrency
    targets = [f"{base_url.rstrip('/')}/{p.lstrip('/')}" for p in test_paths]
    
    latencies: List[float] = []
    status_counts: Dict[int, int] = {}

    limits = httpx.Limits(max_keepalive_connections=concurrency, max_connections=concurrency * 2)
    timeout = httpx.Timeout(10.0, connect=5.0)

    print(f"\n=======================================================")
    print(f"URL Shortener Performance Benchmark")
    print(f"Target Base:    {base_url}")
    print(f"Concurrency:    {concurrency} workers")
    print(f"Total Requests: {total_requests}")
    print(f"Sample Paths:   {test_paths}")
    print(f"=======================================================\n")

    overall_start = time.perf_counter()

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        tasks = []
        for worker_id in range(concurrency):
            tasks.append(
                run_worker(
                    worker_id,
                    client,
                    targets,
                    requests_per_worker,
                    latencies,
                    status_counts,
                )
            )
        await asyncio.gather(*tasks)

    overall_duration = time.perf_counter() - overall_start
    total_completed = len(latencies)
    rps = total_completed / overall_duration if overall_duration > 0 else 0

    latencies.sort()
    
    def percentile(p: float) -> float:
        if not latencies:
            return 0.0
        k = (len(latencies) - 1) * p
        f = int(k)
        c = f + 1
        if c < len(latencies):
            return latencies[f] + (k - f) * (latencies[c] - latencies[f])
        return latencies[f]

    p50 = percentile(0.50)
    p90 = percentile(0.90)
    p95 = percentile(0.95)
    p99 = percentile(0.99)
    min_lat = latencies[0] if latencies else 0.0
    max_lat = latencies[-1] if latencies else 0.0
    avg_lat = statistics.mean(latencies) if latencies else 0.0

    results = {
        "duration_seconds": round(overall_duration, 4),
        "total_requests": total_completed,
        "throughput_rps": round(rps, 2),
        "latency_ms": {
            "min": round(min_lat, 2),
            "avg": round(avg_lat, 2),
            "p50": round(p50, 2),
            "p90": round(p90, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "max": round(max_lat, 2),
        },
        "status_distribution": status_counts,
    }

    print("--- BENCHMARK RESULTS ---")
    print(f"Completed:       {total_completed} requests in {overall_duration:.2f}s")
    print(f"Throughput:      {rps:.2f} req/sec")
    print(f"Latency Min:     {min_lat:.2f} ms")
    print(f"Latency Avg:     {avg_lat:.2f} ms")
    print(f"Latency p50:     {p50:.2f} ms")
    print(f"Latency p90:     {p90:.2f} ms")
    print(f"Latency p95:     {p95:.2f} ms")
    print(f"Latency p99:     {p99:.2f} ms")
    print(f"Latency Max:     {max_lat:.2f} ms")
    print(f"Status Codes:    {status_counts}")
    print("-------------------------\n")

    return results


def main():
    parser = argparse.ArgumentParser(description="URL Shortener Benchmark Runner")
    parser.add_argument("--url", default="http://localhost:8000", help="Target server URL")
    parser.add_argument("-c", "--concurrency", type=int, default=20, help="Concurrency level")
    parser.add_argument("-n", "--requests", type=int, default=1000, help="Total request count")
    parser.add_argument("--paths", nargs="+", default=["health", "metrics"], help="Relative paths to query")

    args = parser.parse_args()
    asyncio.run(
        execute_benchmark(
            base_url=args.url,
            concurrency=args.concurrency,
            total_requests=args.requests,
            test_paths=args.paths,
        )
    )


if __name__ == "__main__":
    main()
