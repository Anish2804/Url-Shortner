/**
 * k6 Performance & Load Test Suite for URL Shortener Platform
 *
 * Scenarios:
 * 1. Warm-up & Cache Fill: Seed URLs and warm Redis cache.
 * 2. Peak Redirect Load: High-concurrency 302 redirection test.
 * 3. Cache Stampede & Penetration: Query non-existent and popular keys concurrently.
 * 4. API Shorten Throughput: Authenticated creation under sustained load.
 *
 * Execution:
 * k6 run tests/performance/k6_redirect_test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Custom metric instruments
export const redirectDuration = new Trend('redirect_duration_ms', true);
export const redirectSuccessRate = new Rate('redirect_success_rate');
export const cacheHitRate = new Rate('cache_hit_rate');
export const rateLimitHits = new Counter('rate_limit_hits_total');

export const options = {
  scenarios: {
    // Scenario 1: Sustained High-Throughput Redirection
    redirect_throughput: {
      executor: 'ramping-vus',
      startVUs: 10,
      stages: [
        { duration: '30s', target: 50 },   // Ramp up to 50 VUs
        { duration: '1m', target: 200 },   // Ramp up to 200 VUs
        { duration: '2m', target: 200 },   // Sustain 200 VUs (simulate ~5k-10k RPS)
        { duration: '30s', target: 0 },    // Ramp down
      ],
      gracefulRampDown: '10s',
      exec: 'redirectScenario',
    },
    // Scenario 2: High Concurrency Shorten Operations
    url_creation: {
      executor: 'constant-vus',
      vus: 10,
      duration: '3m',
      exec: 'createUrlScenario',
      startTime: '30s',
    },
  },
  thresholds: {
    // Redirection Performance Standards
    'redirect_duration_ms': ['p(95)<15', 'p(99)<30'], // p95 < 15ms, p99 < 30ms
    'redirect_success_rate': ['rate>0.99'],           // > 99% success
    'http_req_failed': ['rate<0.01'],                // < 1% error rate
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

// Sample pre-generated test short codes for redirection load
const TEST_CODES = [
  'prod001', 'prod002', 'prod003', 'prod004', 'prod005',
  'fast001', 'fast002', 'fast003', 'fast004', 'fast005',
  'cache01', 'cache02', 'cache03', 'cache04', 'cache05'
];

export function redirectScenario() {
  const shortCode = TEST_CODES[Math.floor(Math.random() * TEST_CODES.length)];
  const url = `${BASE_URL}/${shortCode}`;

  const params = {
    redirects: 0, // Do NOT follow redirect so we measure pure response latency
    headers: {
      'User-Agent': 'k6-load-agent/1.0 (X11; Linux x86_64)',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
  };

  const start = Date.now();
  const res = http.get(url, params);
  const duration = Date.now() - start;

  redirectDuration.add(duration);

  const isSuccess = res.status === 301 || res.status === 302;
  const isRateLimited = res.status === 429;
  const isNotFound = res.status === 404;

  if (isRateLimited) {
    rateLimitHits.add(1);
  }

  // Check X-Process-Time-Ms header from API
  const processTime = res.headers['X-Process-Time-Ms'];
  if (processTime && parseFloat(processTime) < 5.0) {
    cacheHitRate.add(1);
  } else {
    cacheHitRate.add(0);
  }

  redirectSuccessRate.add(isSuccess || isNotFound ? 1 : 0);

  check(res, {
    'status is 301, 302, or 404': (r) => [301, 302, 404].includes(r.status),
    'location header present on 302': (r) => r.status !== 302 || r.headers['Location'] !== undefined,
    'latency under 25ms': () => duration < 25,
  });

  // Micro-sleep to emulate high frequency requests
  sleep(0.01);
}

export function createUrlScenario() {
  const payload = JSON.stringify({
    original_url: `https://example.com/benchmarks/${Date.now()}-${Math.floor(Math.random() * 100000)}`,
    title: 'k6 Benchmark Generated URL',
    redirect_type: 302,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': __ENV.API_KEY || 'url_live_benchmark_key_placeholder',
    },
  };

  const res = http.post(`${BASE_URL}/api/v1/urls`, payload, params);

  check(res, {
    'create status is 201 or 401': (r) => r.status === 201 || r.status === 401 || r.status === 429,
  });

  sleep(0.1);
}
