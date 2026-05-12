/**
 * Smoke test — 1 VU, 30s
 * Verifies every critical endpoint responds correctly before a full load run.
 * Run: k6 run tests/load/smoke.js
 */
import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, ADMIN_CREDS } from './config.js';

export const options = {
  vus: 1,
  duration: '30s',
  thresholds: {
    http_req_failed:   ['rate<0.01'],
    http_req_duration: ['p(95)<5000'],
  },
};

export function setup() {
  const res = http.post(
    `${BASE_URL}/login`,
    JSON.stringify(ADMIN_CREDS),
    { headers: { 'Content-Type': 'application/json' } },
  );
  check(res, { 'login OK': (r) => r.status === 200 });
  return { token: res.json('access_token') };
}

export default function (data) {
  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${data.token}`,
  };

  // Health check
  const health = http.get(`${BASE_URL}/health`);
  check(health, { 'health 200': (r) => r.status === 200 });

  // Ask endpoint
  const ask = http.post(
    `${BASE_URL}/ask`,
    JSON.stringify({ session_id: `smoke-${__VU}-${__ITER}`, question: 'What is the annual leave policy?' }),
    { headers },
  );
  check(ask, {
    'ask 200':          (r) => r.status === 200,
    'ask has answer':   (r) => r.json('answer') !== null,
    'ask has agent':    (r) => r.json('agent') !== null,
    'ask confidence>0': (r) => r.json('confidence') > 0,
  });

  // Admin stats
  const stats = http.get(`${BASE_URL}/admin/stats`, { headers });
  check(stats, { 'admin/stats 200': (r) => r.status === 200 });

  sleep(1);
}
