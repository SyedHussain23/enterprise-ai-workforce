/**
 * Stress test — push to 100 VU to find the breaking point.
 *
 * Run AFTER load_test passes. Identifies max throughput before degradation.
 * Run: k6 run tests/load/stress_test.js
 */
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';
import { BASE_URL, ADMIN_CREDS } from './config.js';

const askLatency = new Trend('stress_ask_latency', true);

export const options = {
  stages: [
    { duration: '2m', target: 50  },
    { duration: '2m', target: 100 },
    { duration: '3m', target: 100 },
    { duration: '2m', target: 0   },
  ],
  thresholds: {
    http_req_failed:   ['rate<0.10'],    // tolerate up to 10% errors under stress
    http_req_duration: ['p(95)<8000'],   // relaxed threshold for stress
    stress_ask_latency:['p(95)<8000'],
  },
};

export function setup() {
  const res = http.post(
    `${BASE_URL}/login`,
    JSON.stringify(ADMIN_CREDS),
    { headers: { 'Content-Type': 'application/json' } },
  );
  return { token: res.json('access_token') };
}

export default function (data) {
  const headers = {
    'Content-Type': 'application/json',
    Authorization:  `Bearer ${data.token}`,
  };

  const start = Date.now();
  const res = http.post(
    `${BASE_URL}/ask`,
    JSON.stringify({
      session_id: `stress-${__VU}-${__ITER}`,
      question: 'What is the leave policy?',
    }),
    { headers, timeout: '20s' },
  );
  askLatency.add(Date.now() - start);

  check(res, { 'status 200 or 429': (r) => r.status === 200 || r.status === 429 });
  sleep(0.5);
}
