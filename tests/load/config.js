// Shared config for all k6 load test scripts
export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const ADMIN_CREDS = {
  username: __ENV.ADMIN_USER || 'admin',
  password: __ENV.ADMIN_PASS || 'admin123',
};

export const USER_CREDS = {
  username: __ENV.TEST_USER || 'employee1',
  password: __ENV.TEST_PASS || 'emp123',
};

// Standard thresholds used across all scripts
export const DEFAULT_THRESHOLDS = {
  http_req_failed:   ['rate<0.02'],          // < 2% error rate
  http_req_duration: ['p(95)<3000'],         // 95% of requests under 3s
  http_req_duration: ['p(99)<6000'],         // 99% under 6s
};
