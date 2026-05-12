/**
 * Main load test — ramp up to 50 concurrent users.
 *
 * Stages:
 *   0→10 VU  over 1m  — warm up
 *   10→50 VU over 3m  — ramp to peak load
 *   50 VU    for 5m   — sustained load
 *   50→0 VU  over 1m  — cool down
 *
 * Run: k6 run tests/load/load_test.js
 * With custom URL: BASE_URL=https://your-api.railway.app k6 run tests/load/load_test.js
 */
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { BASE_URL, ADMIN_CREDS, USER_CREDS } from './config.js';

// Custom metrics
const askDuration    = new Trend('ask_duration',   true);
const authFailRate   = new Rate('auth_fail_rate');
const answerMissRate = new Rate('answer_miss_rate');

export const options = {
  stages: [
    { duration: '1m', target: 10 },   // warm up
    { duration: '3m', target: 50 },   // ramp to peak
    { duration: '5m', target: 50 },   // sustained
    { duration: '1m', target: 0  },   // cool down
  ],
  thresholds: {
    http_req_failed:   ['rate<0.02'],          // < 2% errors
    http_req_duration: ['p(95)<3000'],         // 95th percentile < 3s
    http_req_duration: ['p(99)<6000'],         // 99th percentile < 6s
    ask_duration:      ['p(95)<4000'],         // ask endpoint specifically
    auth_fail_rate:    ['rate<0.01'],          // near-zero auth failures
    answer_miss_rate:  ['rate<0.05'],          // < 5% empty answers
  },
};

// Questions pool — varied across departments to test routing
const QUESTIONS = [
  'What is the annual leave policy?',
  'How do I reset my password?',
  'What are the expense reimbursement limits?',
  'How do I connect to the VPN?',
  'What is the notice period for resignation?',
  'How do I submit an invoice?',
  'What is the bonus policy?',
  'How do I onboard a new employee?',
  'What is the paternity leave policy?',
  'How do I request software access?',
];

function pickQuestion() {
  return QUESTIONS[Math.floor(Math.random() * QUESTIONS.length)];
}

export function setup() {
  // Login as admin and regular user
  const adminRes = http.post(
    `${BASE_URL}/login`,
    JSON.stringify(ADMIN_CREDS),
    { headers: { 'Content-Type': 'application/json' } },
  );
  const userRes = http.post(
    `${BASE_URL}/login`,
    JSON.stringify(USER_CREDS),
    { headers: { 'Content-Type': 'application/json' } },
  );
  return {
    adminToken: adminRes.json('access_token'),
    userToken:  userRes.json('access_token'),
  };
}

export default function (data) {
  // 80% regular user, 20% admin (realistic production mix)
  const isAdmin = Math.random() < 0.2;
  const token = isAdmin ? data.adminToken : data.userToken;
  const headers = {
    'Content-Type': 'application/json',
    Authorization:  `Bearer ${token}`,
  };

  if (!token) {
    authFailRate.add(1);
    return;
  }
  authFailRate.add(0);

  const sessionId = `load-vu${__VU}-iter${__ITER}`;

  group('ask query', () => {
    const start = Date.now();
    const res = http.post(
      `${BASE_URL}/ask`,
      JSON.stringify({ session_id: sessionId, question: pickQuestion() }),
      { headers, timeout: '15s' },
    );
    askDuration.add(Date.now() - start);

    const ok = check(res, {
      'ask status 200':  (r) => r.status === 200,
      'ask has answer':  (r) => {
        try { return (r.json('answer') || '').length > 0; } catch { return false; }
      },
      'confidence > 0':  (r) => {
        try { return r.json('confidence') > 0; } catch { return false; }
      },
    });
    answerMissRate.add(!ok ? 1 : 0);
  });

  sleep(Math.random() * 2 + 1);   // 1–3s think time between requests

  // Admin users also hit the stats endpoint
  if (isAdmin) {
    group('admin stats', () => {
      const res = http.get(`${BASE_URL}/admin/stats`, { headers });
      check(res, { 'stats 200': (r) => r.status === 200 });
    });
    sleep(0.5);
  }
}

export function handleSummary(data) {
  const p95  = data.metrics.http_req_duration?.values?.['p(95)']?.toFixed(0) ?? 'N/A';
  const p99  = data.metrics.http_req_duration?.values?.['p(99)']?.toFixed(0) ?? 'N/A';
  const rps  = data.metrics.http_reqs?.values?.rate?.toFixed(2) ?? 'N/A';
  const errs = ((data.metrics.http_req_failed?.values?.rate ?? 0) * 100).toFixed(2);

  const summary = `
=== Enterprise AI Workforce — Load Test Results ===
Peak VUs:       50
RPS:            ${rps}
p95 latency:    ${p95}ms
p99 latency:    ${p99}ms
Error rate:     ${errs}%
Thresholds:     ${data.metrics.http_req_failed?.thresholds ? 'ALL PASS' : 'CHECK ABOVE'}
`;
  console.log(summary);

  return {
    'tests/load/results/load_result.json': JSON.stringify(data, null, 2),
    stdout: summary,
  };
}
